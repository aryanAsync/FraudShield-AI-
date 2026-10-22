"""Feature Preprocessing Module for FraudShield AI.

Provides leakage-free preprocessing pipeline constructing transformers for
Time and Amount features while preserving PCA-derived V1-V28 features.
"""

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import RobustScaler


def get_feature_preprocessor(
    scale_cols: list[str] | None = None,
    passthrough_cols: list[str] | None = None,
) -> ColumnTransformer:
    """Create a ColumnTransformer that scales specified columns and passes through PCA features.

    Uses RobustScaler on Time and Amount to withstand severe outliers while preserving
    the anonymized PCA features V1-V28.

    Args:
        scale_cols: Columns to apply RobustScaler to. Default: ['Time', 'Amount'].
        passthrough_cols: Columns to preserve without scaling. Default: V1-V28.

    Returns:
        Fitted or unfitted ColumnTransformer preserving feature integrity.
    """
    if scale_cols is None:
        scale_cols = ["Time", "Amount"]

    if passthrough_cols is None:
        passthrough_cols = [f"V{i}" for i in range(1, 29)]

    preprocessor = ColumnTransformer(
        transformers=[
            ("scaler", RobustScaler(), scale_cols),
            ("passthrough", "passthrough", passthrough_cols),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    return preprocessor
