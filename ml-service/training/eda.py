"""Exploratory Data Analysis (EDA) Script for FraudShield AI.

Generates visualizations and comprehensive statistical reports on class imbalance,
transaction amount distributions, temporal patterns, and predictive features.
Outputs are saved to reports/ and reports/figures/.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend for headless execution
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import TARGET_COLUMN, get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("eda")

# Set standard aesthetic styling for plots
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["figure.dpi"] = 150


def run_eda(
    data_path: Path,
    reports_dir: Path,
) -> dict[str, Any]:
    """Execute exploratory data analysis and generate report artifacts.

    Args:
        data_path: Path to dataset CSV.
        reports_dir: Base directory for reports.

    Returns:
        Summary statistics dictionary.
    """
    logger.info("Loading dataset from %s for EDA...", data_path)
    df = pd.read_csv(data_path)

    figures_dir = reports_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    legit = df[df[TARGET_COLUMN] == 0]
    fraud = df[df[TARGET_COLUMN] == 1]
    total_count = len(df)
    legit_count = len(legit)
    fraud_count = len(fraud)
    fraud_ratio = fraud_count / total_count

    logger.info("Dataset shape: %s (Legit: %d, Fraud: %d)", df.shape, legit_count, fraud_count)

    # 1. Plot: Class Distribution
    logger.info("Generating class distribution plot...")
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Linear count
    sns.countplot(x=TARGET_COLUMN, data=df, ax=axes[0], palette=["#2ecc71", "#e74c3c"])
    axes[0].set_title("Class Frequency (Linear Scale)", fontsize=13, fontweight="bold")
    axes[0].set_xticklabels(["Legitimate (0)", "Fraud (1)"])
    axes[0].set_ylabel("Count")
    for p in axes[0].patches:
        height = p.get_height()
        axes[0].annotate(
            f"{int(height):,}\n({height / total_count:.2%})",
            (p.get_x() + p.get_width() / 2.0, height / 2.0),
            ha="center",
            va="center",
            color="white",
            fontweight="bold",
            fontsize=11,
        )

    # Log count to visualize the severe imbalance
    sns.countplot(x=TARGET_COLUMN, data=df, ax=axes[1], palette=["#2ecc71", "#e74c3c"])
    axes[1].set_yscale("log")
    axes[1].set_title("Class Frequency (Logarithmic Scale)", fontsize=13, fontweight="bold")
    axes[1].set_xticklabels(["Legitimate (0)", "Fraud (1)"])
    axes[1].set_ylabel("Log Count")
    for p in axes[1].patches:
        height = p.get_height()
        axes[1].annotate(
            f"{int(height):,}",
            (p.get_x() + p.get_width() / 2.0, height * 0.4),
            ha="center",
            va="center",
            color="white",
            fontweight="bold",
            fontsize=11,
        )

    plt.tight_layout()
    fig.savefig(figures_dir / "class_distribution.png")
    plt.close(fig)

    # 2. Plot: Transaction Amount Distribution
    logger.info("Generating transaction amount distribution plot...")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Boxplot on log-transformed amount
    df_plot = df.copy()
    df_plot["Log_Amount"] = np.log1p(df_plot["Amount"])

    sns.boxplot(
        x=TARGET_COLUMN,
        y="Log_Amount",
        data=df_plot,
        palette=["#2ecc71", "#e74c3c"],
        ax=axes[0],
    )
    axes[0].set_title("Log(Amount + 1) Comparison", fontsize=13, fontweight="bold")
    axes[0].set_xticklabels(["Legitimate (0)", "Fraud (1)"])
    axes[0].set_ylabel("log(Amount + 1)")

    # KDE distribution overlay
    sns.kdeplot(
        df_plot[df_plot[TARGET_COLUMN] == 0]["Log_Amount"],
        label="Legitimate",
        color="#2ecc71",
        fill=True,
        alpha=0.3,
        ax=axes[1],
    )
    sns.kdeplot(
        df_plot[df_plot[TARGET_COLUMN] == 1]["Log_Amount"],
        label="Fraud",
        color="#e74c3c",
        fill=True,
        alpha=0.4,
        ax=axes[1],
    )
    axes[1].set_title("Density of Log(Amount + 1)", fontsize=13, fontweight="bold")
    axes[1].set_xlabel("log(Amount + 1)")
    axes[1].legend()

    plt.tight_layout()
    fig.savefig(figures_dir / "amount_distribution.png")
    plt.close(fig)

    # 3. Plot: Time Distribution (approx 48 hours span)
    logger.info("Generating transaction time distribution plot...")
    fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True)

    time_hours_legit = legit["Time"] / 3600.0
    time_hours_fraud = fraud["Time"] / 3600.0

    sns.histplot(time_hours_legit, bins=48, ax=axes[0], color="#3498db", kde=True)
    axes[0].set_title("Legitimate Transactions over Time (Hours)", fontsize=12, fontweight="bold")
    axes[0].set_ylabel("Count")

    sns.histplot(time_hours_fraud, bins=48, ax=axes[1], color="#e74c3c", kde=True)
    axes[1].set_title("Fraudulent Transactions over Time (Hours)", fontsize=12, fontweight="bold")
    axes[1].set_xlabel("Time elapsed (Hours)")
    axes[1].set_ylabel("Count")

    plt.tight_layout()
    fig.savefig(figures_dir / "time_distribution.png")
    plt.close(fig)

    # 4. Feature Correlations with Class
    logger.info("Computing correlations with target label...")
    correlations = df.corr()[TARGET_COLUMN].drop(TARGET_COLUMN)
    sorted_corr = correlations.sort_values()

    fig, ax = plt.subplots(figsize=(10, 8))
    colors = ["#e74c3c" if c < 0 else "#2980b9" for c in sorted_corr.values]
    sorted_corr.plot(kind="barh", ax=ax, color=colors)
    ax.set_title("Feature Correlation with Fraud Label (Class)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Pearson Correlation Coefficient")
    ax.axvline(0, color="black", linestyle="--", alpha=0.6)
    plt.tight_layout()
    fig.savefig(figures_dir / "feature_correlations.png")
    plt.close(fig)

    # 5. Selected Top Discriminative Feature Distributions
    # Top 3 negatively and top 3 positively correlated features
    top_negative = sorted_corr.head(3).index.tolist()
    top_positive = sorted_corr.tail(3).index.tolist()
    selected_features = top_negative + top_positive

    logger.info("Generating boxplots for top discriminative features: %s", selected_features)
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    axes = axes.flatten()

    for idx, feature in enumerate(selected_features):
        sns.boxplot(
            x=TARGET_COLUMN,
            y=feature,
            data=df,
            ax=axes[idx],
            palette=["#2ecc71", "#e74c3c"],
            showfliers=False,  # Hide extreme outliers for clear visual comparison of distributions
        )
        axes[idx].set_title(
            f"{feature} Distribution (Outliers hidden)", fontsize=11, fontweight="bold"
        )
        axes[idx].set_xticklabels(["Legit (0)", "Fraud (1)"])

    plt.tight_layout()
    fig.savefig(figures_dir / "selected_features_distribution.png")
    plt.close(fig)

    # Summary Statistics Compilation
    amount_legit_stats = legit["Amount"].describe().to_dict()
    amount_fraud_stats = fraud["Amount"].describe().to_dict()

    summary_stats: dict[str, Any] = {
        "dataset_shape": {
            "rows": total_count,
            "columns": len(df.columns),
        },
        "class_imbalance": {
            "legitimate_cases": legit_count,
            "fraud_cases": fraud_count,
            "fraud_percentage": round(fraud_ratio * 100.0, 4),
            "imbalance_ratio": f"1:{int(round(legit_count / fraud_count))}",
        },
        "amount_statistics": {
            "legitimate": {k: round(float(v), 2) for k, v in amount_legit_stats.items()},
            "fraudulent": {k: round(float(v), 2) for k, v in amount_fraud_stats.items()},
        },
        "time_statistics": {
            "total_span_hours": round(float(df["Time"].max() / 3600.0), 2),
            "median_time_seconds": round(float(df["Time"].median()), 2),
        },
        "top_correlated_features": {
            "strongest_negative": {
                feat: round(float(val), 4) for feat, val in sorted_corr.head(5).items()
            },
            "strongest_positive": {
                feat: round(float(val), 4) for feat, val in sorted_corr.tail(5).iloc[::-1].items()
            },
        },
        "generated_plots": [
            "figures/class_distribution.png",
            "figures/amount_distribution.png",
            "figures/time_distribution.png",
            "figures/feature_correlations.png",
            "figures/selected_features_distribution.png",
        ],
    }

    # Save JSON summary
    summary_json_path = reports_dir / "eda_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_stats, f, indent=2)
    logger.info("Saved EDA JSON summary to %s", summary_json_path)

    # Save Markdown summary
    summary_md_path = reports_dir / "eda_summary.md"
    with open(summary_md_path, "w", encoding="utf-8") as f:
        f.write("# Exploratory Data Analysis (EDA) Summary\n\n")
        f.write("## 1. Class Imbalance\n")
        f.write(f"- **Total Transactions:** {total_count:,}\n")
        f.write(
            f"- **Legitimate Transactions (0):** {legit_count:,} ({100 - summary_stats['class_imbalance']['fraud_percentage']:.2f}%)\n"
        )
        f.write(
            f"- **Fraudulent Transactions (1):** {fraud_count:,} ({summary_stats['class_imbalance']['fraud_percentage']:.4f}%)\n"
        )
        f.write(f"- **Imbalance Ratio:** {summary_stats['class_imbalance']['imbalance_ratio']}\n\n")
        f.write("## 2. Amount Distribution\n")
        f.write("| Metric | Legitimate ($) | Fraudulent ($) |\n")
        f.write("|---|---|---|\n")
        for k in ["mean", "std", "min", "25%", "50%", "75%", "max"]:
            f.write(
                f"| {k} | {summary_stats['amount_statistics']['legitimate'].get(k)} | {summary_stats['amount_statistics']['fraudulent'].get(k)} |\n"
            )
        f.write("\n## 3. Top Predictive Features (Correlation with Class)\n")
        f.write("### Strongest Negative Correlation (Lower value -> Higher fraud risk):\n")
        for feat, val in summary_stats["top_correlated_features"]["strongest_negative"].items():
            f.write(f"- **{feat}**: {val}\n")
        f.write("\n### Strongest Positive Correlation (Higher value -> Higher fraud risk):\n")
        for feat, val in summary_stats["top_correlated_features"]["strongest_positive"].items():
            f.write(f"- **{feat}**: {val}\n")
        f.write("\n## 4. Visualizations Generated\n")
        for p in summary_stats["generated_plots"]:
            f.write(f"- `{p}`\n")
    logger.info("Saved EDA Markdown report to %s", summary_md_path)

    return summary_stats


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run EDA on Credit Card Fraud Dataset")
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
        help="Directory to save reports and figures",
    )
    args = parser.parse_args()

    data_path = Path(args.data_path)
    reports_dir = Path(args.reports_dir)

    try:
        run_eda(data_path, reports_dir)
        logger.info("EDA completed successfully.")
    except Exception as exc:
        logger.critical("EDA halted with error: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
