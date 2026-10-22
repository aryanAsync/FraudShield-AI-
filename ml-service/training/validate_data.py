"""Dataset Validation Script for FraudShield AI.

Verifies schema integrity, missing values, non-finite values, class label distribution,
and duplicates without silently discarding or altering records.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Add parent directory to path so app.config can be imported if needed
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import EXPECTED_FEATURE_ORDER, TARGET_COLUMN, get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("validate_data")


def validate_dataset(csv_path: Path, output_report_path: Path | None = None) -> dict[str, Any]:
    """Execute comprehensive validation on credit card transaction dataset.

    Args:
        csv_path: Path to the raw CSV file.
        output_report_path: Optional path to save JSON validation report.

    Returns:
        Dictionary containing validation findings.

    Raises:
        FileNotFoundError: If dataset does not exist.
        ValueError: If critical validation checks fail.
    """
    logger.info("Starting dataset validation on: %s", csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset file not found at: {csv_path}")

    # Load dataset
    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:
        raise ValueError(f"Failed to read CSV dataset: {exc}") from exc

    total_rows, total_cols = df.shape
    logger.info("Dataset loaded successfully with %d rows and %d columns.", total_rows, total_cols)

    validation_report: dict[str, Any] = {
        "file_path": str(csv_path),
        "total_rows": int(total_rows),
        "total_columns": int(total_cols),
        "columns": df.columns.tolist(),
        "passed": False,
        "critical_errors": [],
        "warnings": [],
        "statistics": {},
    }

    # 1. Column presence check
    expected_columns = EXPECTED_FEATURE_ORDER + [TARGET_COLUMN]
    missing_columns = [col for col in expected_columns if col not in df.columns]
    unexpected_columns = [col for col in df.columns if col not in expected_columns]

    if missing_columns:
        err = f"Missing required columns: {missing_columns}"
        validation_report["critical_errors"].append(err)
        logger.error(err)

    if unexpected_columns:
        warn = f"Unexpected columns found: {unexpected_columns}"
        validation_report["warnings"].append(warn)
        logger.warning(warn)

    # 2. Data Types & Non-finite checks
    missing_counts = df.isnull().sum().to_dict()
    total_missing = sum(missing_counts.values())
    validation_report["statistics"]["missing_values_by_column"] = {
        col: int(cnt) for col, cnt in missing_counts.items() if cnt > 0
    }
    validation_report["statistics"]["total_missing_values"] = int(total_missing)

    if total_missing > 0:
        err = f"Dataset contains {total_missing} missing (NaN/null) values across columns."
        validation_report["critical_errors"].append(err)
        logger.error(err)

    # Non-finite values (infinite or negative infinite)
    non_finite_counts = {}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            inf_count = np.isinf(df[col]).sum()
            if inf_count > 0:
                non_finite_counts[col] = int(inf_count)

    validation_report["statistics"]["infinite_values_by_column"] = non_finite_counts
    if non_finite_counts:
        err = f"Dataset contains non-finite (inf/-inf) values: {non_finite_counts}"
        validation_report["critical_errors"].append(err)
        logger.error(err)

    # 3. Target column validation
    if TARGET_COLUMN in df.columns:
        unique_labels = df[TARGET_COLUMN].dropna().unique().tolist()
        validation_report["statistics"]["unique_labels"] = unique_labels

        if not set(unique_labels).issubset({0, 1}):
            err = f"Target '{TARGET_COLUMN}' contains invalid labels: {unique_labels}. Expected only {{0, 1}}."
            validation_report["critical_errors"].append(err)
            logger.error(err)

        class_counts = df[TARGET_COLUMN].value_counts().to_dict()
        legit_count = int(class_counts.get(0, 0))
        fraud_count = int(class_counts.get(1, 0))
        fraud_percentage = (fraud_count / total_rows * 100.0) if total_rows > 0 else 0.0

        validation_report["statistics"]["legitimate_count"] = legit_count
        validation_report["statistics"]["fraud_count"] = fraud_count
        validation_report["statistics"]["fraud_percentage"] = round(fraud_percentage, 5)

        logger.info(
            "Class distribution: Legitimate (0)=%d, Fraud (1)=%d (%.4f%% fraud rate)",
            legit_count,
            fraud_count,
            fraud_percentage,
        )

    # 4. Duplicate rows analysis (do not discard automatically)
    duplicate_mask = df.duplicated()
    num_duplicates = int(duplicate_mask.sum())
    validation_report["statistics"]["duplicate_rows_count"] = num_duplicates

    if num_duplicates > 0:
        fraud_duplicates = int(df[duplicate_mask & (df[TARGET_COLUMN] == 1)].shape[0])
        legit_duplicates = num_duplicates - fraud_duplicates
        warn = (
            f"Found {num_duplicates} duplicate records ({legit_duplicates} legitimate, "
            f"{fraud_duplicates} fraudulent). Duplicates should be analyzed in EDA rather than "
            f"silently removed."
        )
        validation_report["warnings"].append(warn)
        logger.warning(warn)

    # 5. Amount and Time ranges
    if "Amount" in df.columns:
        validation_report["statistics"]["amount_summary"] = {
            "min": float(df["Amount"].min()),
            "max": float(df["Amount"].max()),
            "mean": float(round(df["Amount"].mean(), 2)),
            "median": float(round(df["Amount"].median(), 2)),
        }
    if "Time" in df.columns:
        validation_report["statistics"]["time_summary"] = {
            "min": float(df["Time"].min()),
            "max": float(df["Time"].max()),
            "span_seconds": float(df["Time"].max() - df["Time"].min()),
            "span_hours": float(round((df["Time"].max() - df["Time"].min()) / 3600.0, 2)),
        }

    # Final verdict
    validation_report["passed"] = len(validation_report["critical_errors"]) == 0

    if output_report_path:
        output_report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_report_path, "w", encoding="utf-8") as f:
            json.dump(validation_report, f, indent=2)
        logger.info("Validation report written to: %s", output_report_path)

    if not validation_report["passed"]:
        error_msg = (
            f"Data validation failed with critical errors: {validation_report['critical_errors']}"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info("Data validation PASSED successfully.")
    return validation_report


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Validate Credit Card Fraud Dataset")
    parser.add_argument(
        "--data-path",
        type=str,
        default=str(settings.resolve_dataset_path()),
        help="Path to creditcard.csv",
    )
    parser.add_argument(
        "--report-path",
        type=str,
        default="reports/data_validation_report.json",
        help="Path to save output validation report JSON",
    )
    args = parser.parse_args()

    csv_path = Path(args.data_path)
    report_path = Path(args.report_path)

    try:
        report = validate_dataset(csv_path, report_path)
        print("\n" + "=" * 60)
        print(" DATASET VALIDATION SUMMARY")
        print("=" * 60)
        print(f"File:               {report['file_path']}")
        print(f"Total Rows:         {report['total_rows']:,}")
        print(f"Total Columns:      {report['total_columns']}")
        print(f"Legitimate Cases:   {report['statistics'].get('legitimate_count', 0):,}")
        print(f"Fraudulent Cases:   {report['statistics'].get('fraud_count', 0):,}")
        print(f"Fraud Percentage:   {report['statistics'].get('fraud_percentage', 0.0):.4f}%")
        print(f"Duplicates:         {report['statistics'].get('duplicate_rows_count', 0):,}")
        print(f"Total Missing:      {report['statistics'].get('total_missing_values', 0)}")
        print(f"Status:             {'PASSED' if report['passed'] else 'FAILED'}")
        print("=" * 60 + "\n")
    except Exception as exc:
        logger.critical("Validation halted: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
