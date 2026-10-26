"""Model Comparison and Artifact Selection Pipeline for FraudShield AI.

Trains and compares candidate classifiers (Logistic Regression, Random Forest, XGBoost)
using chronological data splitting, threshold optimization on validation data, and unbiased
final evaluation on the untouched test set. Saves the winning model artifact with metadata.
"""

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import EXPECTED_FEATURE_ORDER, TARGET_COLUMN, get_settings
from app.ml.preprocessing import get_feature_preprocessor
from training.evaluate import (
    calculate_metrics,
    find_optimal_threshold,
    plot_confusion_matrix,
    plot_precision_recall_curve,
)
from training.train import chronological_split

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("compare_models")


class KMeansAnomalyClassifier(BaseEstimator, ClassifierMixin):
    """K-Means clustering anomaly and fraud detector.
    Computes cluster fraud propensity and centroid distance to produce calibrated fraud probabilities.
    """

    def __init__(self, n_clusters: int = 8, random_state: int = 42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.kmeans = KMeans(n_clusters=self.n_clusters, random_state=self.random_state, n_init=10)
        self.cluster_fraud_prob_: np.ndarray | None = None
        self.classes_ = np.array([0, 1])
        self.max_dist_ = 1.0

    def fit(self, X, y=None):
        X_arr = np.asarray(X)
        self.kmeans.fit(X_arr)
        if y is not None:
            labels = self.kmeans.labels_
            y_arr = np.asarray(y)
            self.cluster_fraud_prob_ = np.zeros(self.n_clusters)
            for c in range(self.n_clusters):
                mask = labels == c
                if np.sum(mask) > 0:
                    self.cluster_fraud_prob_[c] = np.mean(y_arr[mask])
                else:
                    self.cluster_fraud_prob_[c] = 0.0
        distances = np.min(self.kmeans.transform(X_arr), axis=1)
        self.max_dist_ = float(np.percentile(distances, 98) + 1e-6)
        return self

    def predict_proba(self, X):
        X_arr = np.asarray(X)
        cluster_idx = self.kmeans.predict(X_arr)
        distances = np.min(self.kmeans.transform(X_arr), axis=1)
        norm_dist = np.clip(distances / self.max_dist_, 0.0, 1.0)

        if self.cluster_fraud_prob_ is not None:
            base_p1 = self.cluster_fraud_prob_[cluster_idx]
            p1 = np.clip(0.65 * base_p1 + 0.35 * (norm_dist * 0.15), 0.0, 1.0)
        else:
            p1 = norm_dist

        p0 = 1.0 - p1
        return np.column_stack([p0, p1])

    def predict(self, X):
        proba = self.predict_proba(X)
        return (proba[:, 1] >= 0.5).astype(int)


def build_candidate_models(train_df: pd.DataFrame) -> dict[str, Any]:
    """Define candidate classification models with appropriate imbalanced-class configurations."""
    n_legit = int((train_df[TARGET_COLUMN] == 0).sum())
    n_fraud = int((train_df[TARGET_COLUMN] == 1).sum())
    scale_pos_weight = float(n_legit / max(n_fraud, 1))

    logger.info(
        "Candidate model setup: Train legit=%d, fraud=%d, scale_pos_weight=%.2f",
        n_legit,
        n_fraud,
        scale_pos_weight,
    )

    models = {
        "RandomForest": RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
        "XGBoost": XGBClassifier(
            n_estimators=150,
            max_depth=5,
            learning_rate=0.08,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
        ),
        "DecisionTree": DecisionTreeClassifier(
            max_depth=8,
            class_weight="balanced",
            random_state=42,
        ),
        "KNN": KNeighborsClassifier(
            n_neighbors=5,
            weights="distance",
            n_jobs=-1,
        ),
        "LogisticRegression": LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            random_state=42,
            solver="lbfgs",
        ),
        "Clustering": KMeansAnomalyClassifier(
            n_clusters=8,
            random_state=42,
        ),
        "NaiveBayes": GaussianNB(),
    }
    return models


def run_model_comparison(
    data_path: Path,
    reports_dir: Path,
    artifact_path: Path,
    model_version: str = "fraud-model-v1",
) -> dict[str, Any]:
    """Train multiple candidate models, select best on validation, evaluate on test, and save artifact."""
    logger.info("Loading dataset for model comparison from: %s", data_path)
    df = pd.read_csv(data_path)

    # 1. Chronological Split (70% train, 15% validation, 15% test)
    train_df, val_df, test_df = chronological_split(df, 0.70, 0.15, 0.15)

    X_train = train_df[EXPECTED_FEATURE_ORDER]
    y_train = train_df[TARGET_COLUMN].values

    X_val = val_df[EXPECTED_FEATURE_ORDER]
    y_val = val_df[TARGET_COLUMN].values

    X_test = test_df[EXPECTED_FEATURE_ORDER]
    y_test = test_df[TARGET_COLUMN].values

    candidates = build_candidate_models(train_df)
    comparison_results: list[dict[str, Any]] = []
    trained_pipelines: dict[str, Pipeline] = {}
    optimal_thresholds: dict[str, float] = {}

    figures_dir = reports_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # 2. Train and Validate Candidates
    for name, classifier in candidates.items():
        logger.info("\n" + "=" * 50)
        logger.info("Training candidate model: %s", name)
        logger.info("=" * 50)

        preprocessor = get_feature_preprocessor()
        pipeline = Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("classifier", classifier),
            ]
        )

        pipeline.fit(X_train, y_train)
        trained_pipelines[name] = pipeline

        # Predict probabilities on validation set
        val_proba = pipeline.predict_proba(X_val)[:, 1]

        # Optimize threshold on validation data (maximizing F1)
        best_thresh, best_f1, _ = find_optimal_threshold(
            y_val,
            val_proba,
            metric="f1",
            min_threshold=0.05,
            max_threshold=0.95,
            num_steps=181,
        )
        optimal_thresholds[name] = best_thresh

        # Validation metrics at optimal threshold
        val_metrics = calculate_metrics(y_val, val_proba, threshold=best_thresh)
        val_metrics_std = calculate_metrics(y_val, val_proba, threshold=0.50)

        logger.info(
            "[%s] Val Optimal (Thresh=%.4f) -> Precision: %.4f, Recall: %.4f, F1: %.4f, PR-AUC: %.4f",
            name,
            best_thresh,
            val_metrics["precision"],
            val_metrics["recall"],
            val_metrics["f1_score"],
            val_metrics["pr_auc"],
        )

        comparison_results.append(
            {
                "model_name": name,
                "optimal_threshold": round(best_thresh, 4),
                "val_f1_score": val_metrics["f1_score"],
                "val_pr_auc": val_metrics["pr_auc"],
                "val_roc_auc": val_metrics["roc_auc"],
                "val_precision": val_metrics["precision"],
                "val_recall": val_metrics["recall"],
                "val_metrics_optimal": val_metrics,
                "val_metrics_default": val_metrics_std,
            }
        )

    # 3. Model Selection based on Validation PR-AUC and F1
    # PR-AUC is primary for severe class imbalance; F1 confirms threshold effectiveness
    comparison_results.sort(
        key=lambda r: (r["val_pr_auc"], r["val_f1_score"]),
        reverse=True,
    )
    winning_info = comparison_results[0]
    winning_model_name = winning_info["model_name"]
    winning_threshold = winning_info["optimal_threshold"]
    winning_pipeline = trained_pipelines[winning_model_name]

    logger.info("\n" + "#" * 60)
    logger.info(
        "WINNING MODEL SELECTED: %s (Val PR-AUC: %.4f, Val F1: %.4f)",
        winning_model_name,
        winning_info["val_pr_auc"],
        winning_info["val_f1_score"],
    )
    logger.info("#" * 60 + "\n")

    # 4. Final Evaluation on Untouched TEST Set (Only for the Winning Model!)
    logger.info(
        "Evaluating winning model (%s) on untouched Test Set (%d samples)...",
        winning_model_name,
        len(X_test),
    )
    test_proba = winning_pipeline.predict_proba(X_test)[:, 1]
    test_metrics = calculate_metrics(y_test, test_proba, threshold=winning_threshold)

    logger.info(
        "TEST SET RESULTS for %s (Threshold=%.4f):\n"
        " - Precision: %.4f\n"
        " - Recall:    %.4f\n"
        " - F1-Score:  %.4f\n"
        " - PR-AUC:    %.4f\n"
        " - ROC-AUC:   %.4f\n"
        " - Confusion Matrix: TN=%d, FP=%d, FN=%d, TP=%d",
        winning_model_name,
        winning_threshold,
        test_metrics["precision"],
        test_metrics["recall"],
        test_metrics["f1_score"],
        test_metrics["pr_auc"],
        test_metrics["roc_auc"],
        test_metrics["confusion_matrix"]["true_negatives"],
        test_metrics["confusion_matrix"]["false_positives"],
        test_metrics["confusion_matrix"]["false_negatives"],
        test_metrics["confusion_matrix"]["true_positives"],
    )

    # 5. Generate and Save Test Figures
    plot_confusion_matrix(
        test_metrics["confusion_matrix"],
        f"Final Test Confusion Matrix - {winning_model_name} (Thresh={winning_threshold:.2f})",
        figures_dir / "test_confusion_matrix.png",
    )
    plot_precision_recall_curve(
        y_test,
        test_proba,
        winning_threshold,
        f"{winning_model_name} (Final Test Set)",
        figures_dir / "test_pr_curve.png",
    )

    # 6. Save Comparison Reports (JSON and Markdown)
    report_data = {
        "evaluation_timestamp": datetime.now(UTC).isoformat(),
        "selected_model": winning_model_name,
        "selected_threshold": winning_threshold,
        "validation_comparison": comparison_results,
        "final_test_evaluation": {
            "model_name": winning_model_name,
            "threshold": winning_threshold,
            "test_metrics": test_metrics,
        },
    }

    report_json_path = reports_dir / "model_comparison.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    logger.info("Saved model comparison JSON to: %s", report_json_path)

    report_md_path = reports_dir / "model_comparison.md"
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("# Model Comparison & Final Evaluation Report\n\n")
        f.write(f"- **Selected Winning Model:** `{winning_model_name}`\n")
        f.write(f"- **Selected Operating Threshold:** `{winning_threshold:.4f}`\n")
        f.write(f"- **Evaluation Timestamp:** `{report_data['evaluation_timestamp']}`\n\n")
        f.write("## 1. Validation Set Model Comparison\n\n")
        f.write(
            "| Model | Optimal Threshold | Val Precision | Val Recall | Val F1-Score | Val PR-AUC | Val ROC-AUC |\n"
        )
        f.write("|---|---|---|---|---|---|---|\n")
        for res in comparison_results:
            f.write(
                f"| **{res['model_name']}** | {res['optimal_threshold']:.4f} | "
                f"{res['val_precision']:.4f} | {res['val_recall']:.4f} | "
                f"{res['val_f1_score']:.4f} | {res['val_pr_auc']:.4f} | "
                f"{res['val_roc_auc']:.4f} |\n"
            )

        f.write("\n## 2. Final Test Set Evaluation (Selected Model)\n\n")
        f.write(
            f"Evaluated on untouched test partition ({len(X_test):,} transactions, {int(y_test.sum())} fraud cases):\n\n"
        )
        f.write(f"- **Precision:** {test_metrics['precision']:.4f}\n")
        f.write(f"- **Recall:** {test_metrics['recall']:.4f}\n")
        f.write(f"- **F1-Score:** {test_metrics['f1_score']:.4f}\n")
        f.write(f"- **PR-AUC (Average Precision):** {test_metrics['pr_auc']:.4f}\n")
        f.write(f"- **ROC-AUC:** {test_metrics['roc_auc']:.4f}\n\n")
        f.write("### Test Confusion Matrix\n\n")
        f.write("| | Predicted Legitimate (0) | Predicted Fraudulent (1) |\n")
        f.write("|---|---|---|\n")
        f.write(
            f"| **Actual Legitimate (0)** | {test_metrics['confusion_matrix']['true_negatives']:,} (TN) | {test_metrics['confusion_matrix']['false_positives']:,} (FP) |\n"
        )
        f.write(
            f"| **Actual Fraudulent (1)** | {test_metrics['confusion_matrix']['false_negatives']:,} (FN) | {test_metrics['confusion_matrix']['true_positives']:,} (TP) |\n\n"
        )
        f.write("## 3. Visual Artifacts\n\n")
        f.write("- Test Confusion Matrix: `figures/test_confusion_matrix.png`\n")
        f.write("- Test Precision-Recall Curve: `figures/test_pr_curve.png`\n")
    logger.info("Saved model comparison Markdown report to: %s", report_md_path)

    # 7. Model Artifact Management - Save Complete Bundle
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_metadata = {
        "model_version": model_version,
        "model_type": winning_model_name,
        "feature_names": EXPECTED_FEATURE_ORDER,
        "expected_feature_order": EXPECTED_FEATURE_ORDER,
        "selected_threshold": winning_threshold,
        "pipeline": winning_pipeline,
        "training_dataset_description": (
            f"Credit Card Fraud Detection Dataset (284,807 transactions, 492 fraud cases). "
            f"Chronological split: 70% train ({len(train_df)}), 15% val ({len(val_df)}), "
            f"15% test ({len(test_df)})."
        ),
        "training_config": {
            "train_ratio": 0.70,
            "val_ratio": 0.15,
            "test_ratio": 0.15,
            "random_seed": 42,
            "scaler": "RobustScaler(Time, Amount)",
            "selected_model": winning_model_name,
        },
        "validation_metrics": winning_info["val_metrics_optimal"],
        "test_metrics": test_metrics,
        "created_at": datetime.now(UTC).isoformat(),
    }

    joblib.dump(artifact_metadata, artifact_path)
    logger.info("Successfully serialized winning model artifact to: %s", artifact_path)

    return report_data


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Compare ML Models and Export Artifact")
    parser.add_argument(
        "--data-path",
        type=str,
        default=str(settings.resolve_dataset_path()),
        help="Path to creditcard.csv",
    )
    parser.add_argument(
        "--reports-dir",
        type=str,
        default="reports",
        help="Directory to save comparison reports and plots",
    )
    parser.add_argument(
        "--artifact-path",
        type=str,
        default=str(settings.resolve_artifact_path()),
        help="Destination path for serialized model artifact",
    )
    parser.add_argument(
        "--model-version",
        type=str,
        default=settings.MODEL_VERSION,
        help="Version string for model artifact",
    )
    args = parser.parse_args()

    data_path = Path(args.data_path)
    reports_dir = Path(args.reports_dir)
    artifact_path = Path(args.artifact_path)

    run_model_comparison(data_path, reports_dir, artifact_path, args.model_version)


if __name__ == "__main__":
    main()
