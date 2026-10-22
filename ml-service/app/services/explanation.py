"""Model Explanation Service using SHAP for FraudShield AI.

Generates feature attributions for fraud predictions using TreeExplainer.
Handles anonymized PCA features responsibly and fails gracefully without
blocking inference if explanations are unavailable or disabled.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd
import shap
from sklearn.pipeline import Pipeline

from app.schemas.prediction import FeatureAttribution

logger = logging.getLogger("explanation_service")


class ExplanationService:
    """Provides SHAP-based feature attribution for tree-based fraud detection models."""

    def __init__(self, pipeline: Pipeline | None = None, enabled: bool = True):
        self.enabled = enabled
        self.explainer: Any | None = None
        self.preprocessor: Any | None = None
        self.classifier: Any | None = None
        self.feature_names: list[str] = []

        if pipeline is not None and enabled:
            self._initialize_explainer(pipeline)

    def _initialize_explainer(self, pipeline: Pipeline) -> None:
        """Initialize TreeExplainer from fitted pipeline steps."""
        try:
            self.preprocessor = pipeline.named_steps["preprocessor"]
            self.classifier = pipeline.named_steps["classifier"]

            # Initialize SHAP TreeExplainer on classifier
            logger.info("Initializing SHAP TreeExplainer for %s...", type(self.classifier).__name__)
            self.explainer = shap.TreeExplainer(self.classifier)
            logger.info("SHAP TreeExplainer initialized successfully.")
        except Exception as exc:
            logger.warning(
                "Could not initialize SHAP explainer: %s. Explanations will be disabled.", exc
            )
            self.explainer = None
            self.enabled = False

    def explain_instance(
        self,
        df_row: pd.DataFrame,
        top_k: int = 5,
    ) -> list[FeatureAttribution] | None:
        """Compute top feature attributions for a single transaction.

        Args:
            df_row: Single-row DataFrame matching training feature schema.
            top_k: Number of most impactful features to return.

        Returns:
            List of FeatureAttribution objects or None if explanation fails.
        """
        if not self.enabled or self.explainer is None or self.preprocessor is None:
            return None

        try:
            # Transform features using fitted preprocessor
            transformed_row = self.preprocessor.transform(df_row)

            # Compute SHAP values
            shap_values = self.explainer.shap_values(transformed_row)

            # For binary classification with RandomForest, shap_values is a list [class_0, class_1]
            # or an array of shape (1, num_features, 2)
            if isinstance(shap_values, list) and len(shap_values) == 2:
                # Class 1 (fraud) attributions
                class_1_shap = shap_values[1][0]
            elif isinstance(shap_values, np.ndarray):
                if shap_values.ndim == 3:
                    class_1_shap = shap_values[0, :, 1]
                elif shap_values.ndim == 2:
                    class_1_shap = shap_values[0]
                else:
                    class_1_shap = shap_values
            else:
                return None

            # Get feature names from preprocessor
            try:
                out_feature_names = self.preprocessor.get_feature_names_out()
                clean_names = [f.split("__")[-1] for f in out_feature_names]
            except Exception:
                clean_names = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]

            # Rank features by absolute impact
            ranked_indices = np.argsort(np.abs(class_1_shap))[::-1][:top_k]

            attributions: list[FeatureAttribution] = []
            for idx in ranked_indices:
                feat_name = clean_names[idx]
                raw_value = float(df_row[feat_name].iloc[0]) if feat_name in df_row.columns else 0.0
                attribution_val = float(class_1_shap[idx])

                attributions.append(
                    FeatureAttribution(
                        feature=feat_name,
                        attribution=round(attribution_val, 4),
                        value=round(raw_value, 4),
                    )
                )

            return attributions
        except Exception as exc:
            logger.warning(
                "SHAP explanation calculation failed: %s. Continuing without explanation.", exc
            )
            return None
