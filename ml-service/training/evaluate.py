"""Model Evaluation and Metric Calculation Utilities for FraudShield AI.

Computes precision, recall, F1-score, average precision (PR-AUC), ROC-AUC,
confusion matrix, and tunes decision thresholds based on validation performance.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)

logger = logging.getLogger("evaluate")


def find_optimal_threshold(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    metric: str = "f1",
    min_threshold: float = 0.05,
    max_threshold: float = 0.95,
    num_steps: int = 181,
) -> tuple[float, float, dict[str, float]]:
    """Scan candidate decision thresholds on validation data to optimize a given metric.

    Args:
        y_true: Ground truth binary labels.
        y_proba: Predicted probabilities for the positive class (fraud).
        metric: Optimization target ('f1', 'f2', 'precision', 'recall').
        min_threshold: Lower threshold limit.
        max_threshold: Upper threshold limit.
        num_steps: Number of search steps.

    Returns:
        Tuple of (best_threshold, best_score, score_curve_dict).
    """
    thresholds = np.linspace(min_threshold, max_threshold, num_steps)
    best_thresh = 0.5
    best_score = -1.0
    scores: dict[str, float] = {}

    for t in thresholds:
        y_pred = (y_proba >= t).astype(int)
        if metric == "f1":
            score = f1_score(y_true, y_pred, zero_division=0)
        elif metric == "recall":
            score = recall_score(y_true, y_pred, zero_division=0)
        elif metric == "precision":
            score = precision_score(y_true, y_pred, zero_division=0)
        else:
            score = f1_score(y_true, y_pred, zero_division=0)

        scores[f"{t:.3f}"] = float(score)
        if score > best_score:
            best_score = score
            best_thresh = float(t)

    logger.info(
        "Optimal threshold search complete: Best %s = %.4f at threshold = %.4f",
        metric.upper(),
        best_score,
        best_thresh,
    )
    return best_thresh, best_score, scores


def calculate_metrics(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Calculate comprehensive evaluation metrics at a specific decision threshold.

    Args:
        y_true: Binary ground truth labels.
        y_proba: Predicted probabilities of class 1.
        threshold: Decision threshold for positive classification.

    Returns:
        Structured dictionary of evaluation metrics.
    """
    y_pred = (y_proba >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    pr_auc = average_precision_score(y_true, y_proba)
    roc_auc = roc_auc_score(y_true, y_proba)
    report_dict = classification_report(y_true, y_pred, output_dict=True, zero_division=0)

    # Cost calculation: false negative cost vs false positive investigation cost
    # Assuming standard industry rule: FN (missed fraud) is 10x-20x more expensive than FP (investigation)
    estimated_cost_ratio_10 = (fn * 10) + fp

    metrics: dict[str, Any] = {
        "threshold": round(float(threshold), 4),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1_score": round(float(f1), 4),
        "pr_auc": round(float(pr_auc), 4),
        "roc_auc": round(float(roc_auc), 4),
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
        },
        "classification_report": report_dict,
        "cost_analysis": {
            "fn_cost_weight": 10,
            "fp_cost_weight": 1,
            "estimated_cost_index": int(estimated_cost_ratio_10),
        },
    }
    return metrics


def plot_confusion_matrix(
    cm_dict: dict[str, int],
    title: str,
    output_path: Path,
) -> None:
    """Plot and save a stylized confusion matrix heatmap."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    matrix = np.array(
        [
            [cm_dict["true_negatives"], cm_dict["false_positives"]],
            [cm_dict["false_negatives"], cm_dict["true_positives"]],
        ]
    )

    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(
        matrix,
        annot=True,
        fmt=",d",
        cmap="Blues",
        cbar=False,
        xticklabels=["Pred Legit (0)", "Pred Fraud (1)"],
        yticklabels=["Actual Legit (0)", "Actual Fraud (1)"],
        ax=ax,
        annot_kws={"size": 13, "weight": "bold"},
    )
    ax.set_title(title, fontsize=12, fontweight="bold", pad=12)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    logger.info("Saved confusion matrix plot to: %s", output_path)


def plot_precision_recall_curve(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    selected_threshold: float,
    model_name: str,
    output_path: Path,
) -> None:
    """Plot and save the Precision-Recall curve with the chosen operating threshold highlighted."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    precision, recall, thresholds = precision_recall_curve(y_true, y_proba)
    ap = average_precision_score(y_true, y_proba)

    # Find precision & recall at selected threshold
    y_pred = (y_proba >= selected_threshold).astype(int)
    op_prec = precision_score(y_true, y_pred, zero_division=0)
    op_rec = recall_score(y_true, y_pred, zero_division=0)

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(recall, precision, color="#2980b9", lw=2, label=f"{model_name} (PR-AUC = {ap:.4f})")
    ax.scatter(
        [op_rec],
        [op_prec],
        color="#e74c3c",
        s=100,
        zorder=5,
        label=f"Selected Threshold = {selected_threshold:.2f}\n(Prec={op_prec:.2f}, Rec={op_rec:.2f})",
    )

    ax.set_title(f"Precision-Recall Curve - {model_name}", fontsize=13, fontweight="bold")
    ax.set_xlabel("Recall (Detection Rate)", fontsize=11)
    ax.set_ylabel("Precision (Positive Predictive Value)", fontsize=11)
    ax.set_xlim([0.0, 1.02])
    ax.set_ylim([0.0, 1.02])
    ax.legend(loc="lower left", fontsize=10)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    logger.info("Saved PR curve plot to: %s", output_path)
