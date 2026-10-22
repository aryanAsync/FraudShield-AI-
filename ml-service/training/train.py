"""Baseline Model Training Script for FraudShield AI.

Trains a leakage-safe Logistic Regression baseline using chronological data splitting,
RobustScaler on Time and Amount, balanced class weighting, and threshold tuning on validation set.
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
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import EXPECTED_FEATURE_ORDER, TARGET_COLUMN, get_settings
from app.ml.preprocessing import get_feature_preprocessor
from training.evaluate import (
    calculate_metrics,
    find_optimal_threshold,
    plot_confusion_matrix,
    plot_precision_recall_curve,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("train_baseline")


def chronological_split(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split dataset chronologically based on 'Time' column.

    Ensures no future transactions leak into past training windows.
    Verifies that all splits have sufficient positive fraud instances.
    """
    assert np.isclose(train_ratio + val_ratio + test_ratio, 1.0), "Split ratios must sum to 1.0"

    logger.info("Sorting transactions chronologically by 'Time'...")
    df_sorted = df.sort_values(by="Time").reset_index(drop=True)
    n = len(df_sorted)

    train_end = int(train_ratio * n)
    val_end = int((train_ratio + val_ratio) * n)

    train_df = df_sorted.iloc[:train_end].copy()
    val_df = df_sorted.iloc[train_end:val_end].copy()
    test_df = df_sorted.iloc[val_end:].copy()

    logger.info("Chronological split completed:")
    for name, split in [("Train", train_df), ("Val", val_df), ("Test", test_df)]:
        n_rows = len(split)
        n_fraud = int(split[TARGET_COLUMN].sum())
        logger.info(
            " - %s: %d records (Fraud: %d, %.4f%%)",
            name,
            n_rows,
            n_fraud,
            (n_fraud / n_rows * 100.0) if n_rows > 0 else 0.0,
        )
        if n_fraud == 0:
            raise ValueError(f"{name} split contains 0 fraud examples! Adjust split ratios.")

    return train_df, val_df, test_df


def train_baseline(
    data_path: Path,
    reports_dir: Path,
    artifact_path: Path | None = None,
) -> dict[str, Any]:
    """Train and evaluate the baseline Logistic Regression model."""
    logger.info("Loading dataset from: %s", data_path)
    df = pd.read_csv(data_path)

    # 1. Chronological Split
    train_df, val_df, test_df = chronological_split(df)

    X_train = train_df[EXPECTED_FEATURE_ORDER]
    y_train = train_df[TARGET_COLUMN].values

    X_val = val_df[EXPECTED_FEATURE_ORDER]
    y_val = val_df[TARGET_COLUMN].values

    # 2. Build Pipeline
    logger.info("Constructing Preprocessing & Logistic Regression Pipeline...")
    preprocessor = get_feature_preprocessor()
    classifier = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        random_state=42,
        solver="lbfgs",
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )

    # 3. Fit pipeline on training data only
    logger.info("Fitting baseline pipeline on X_train (%d samples)...", len(X_train))
    pipeline.fit(X_train, y_train)

    # 4. Predict probabilities on Validation set
    logger.info("Evaluating on Validation set (%d samples)...", len(X_val))
    val_proba = pipeline.predict_proba(X_val)[:, 1]

    # 5. Tune Threshold on Validation data
    best_threshold, best_f1, _ = find_optimal_threshold(
        y_val,
        val_proba,
        metric="f1",
        min_threshold=0.05,
        max_threshold=0.95,
        num_steps=181,
    )

    # Compute metrics at standard 0.5 and tuned threshold
    val_metrics_std = calculate_metrics(y_val, val_proba, threshold=0.50)
    val_metrics_opt = calculate_metrics(y_val, val_proba, threshold=best_threshold)

    logger.info(
        "Validation Results (Threshold=0.50): Prec=%.4f, Rec=%.4f, F1=%.4f, PR-AUC=%.4f",
        val_metrics_std["precision"],
        val_metrics_std["recall"],
        val_metrics_std["f1_score"],
        val_metrics_std["pr_auc"],
    )
    logger.info(
        "Validation Results (Threshold=%.4f): Prec=%.4f, Rec=%.4f, F1=%.4f, PR-AUC=%.4f",
        best_threshold,
        val_metrics_opt["precision"],
        val_metrics_opt["recall"],
        val_metrics_opt["f1_score"],
        val_metrics_opt["pr_auc"],
    )

    # 6. Save reports
    reports_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = reports_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    baseline_report: dict[str, Any] = {
        "model_type": "LogisticRegression(class_weight='balanced')",
        "training_time": datetime.now(UTC).isoformat(),
        "optimal_threshold": round(best_threshold, 4),
        "validation_metrics_default_threshold": val_metrics_std,
        "validation_metrics_optimal_threshold": val_metrics_opt,
    }

    report_file = reports_dir / "baseline_evaluation.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(baseline_report, f, indent=2)
    logger.info("Saved baseline evaluation report to %s", report_file)

    plot_confusion_matrix(
        val_metrics_opt["confusion_matrix"],
        f"Baseline Val Confusion Matrix (Thresh={best_threshold:.2f})",
        figures_dir / "confusion_matrix_baseline.png",
    )
    plot_precision_recall_curve(
        y_val,
        val_proba,
        best_threshold,
        "Logistic Regression Baseline",
        figures_dir / "pr_curve_baseline.png",
    )

    if artifact_path:
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_bundle = {
            "model_version": "baseline-lr-v1",
            "model_type": "LogisticRegression",
            "feature_names": EXPECTED_FEATURE_ORDER,
            "expected_feature_order": EXPECTED_FEATURE_ORDER,
            "selected_threshold": best_threshold,
            "pipeline": pipeline,
            "validation_metrics": val_metrics_opt,
            "created_at": datetime.now(UTC).isoformat(),
        }
        joblib.dump(artifact_bundle, artifact_path)
        logger.info("Saved baseline artifact to: %s", artifact_path)

    return baseline_report


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Train Baseline Logistic Regression Model")
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
        help="Directory to save evaluation reports",
    )
    parser.add_argument(
        "--save-artifact",
        action="store_true",
        help="Whether to save the baseline artifact",
    )
    args = parser.parse_args()

    data_path = Path(args.data_path)
    reports_dir = Path(args.reports_dir)
    artifact_path = Path("artifacts/baseline_model.joblib") if args.save_artifact else None

    train_baseline(data_path, reports_dir, artifact_path)


if __name__ == "__main__":
    main()
