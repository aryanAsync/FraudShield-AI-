"""Prediction Service for FraudShield AI.

Coordinates model inference, feature ordering, threshold application,
risk scoring, and optional feature attribution explanations.
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.pipeline import Pipeline

from app.config import (
    EXPECTED_FEATURE_ORDER,
    Settings,
    get_settings,
)
from app.ml.model_loader import load_model_artifact
from app.schemas.prediction import (
    BatchPredictionResponse,
    ModelInfoResponse,
    PredictionResponse,
    PredictionWithExplanationResponse,
    RiskLevel,
)
from app.schemas.transaction import BatchTransactionInput, TransactionInput
from app.services.explanation import ExplanationService

logger = logging.getLogger("predictor_service")


class PredictorService:
    """Manages model lifecycle, inference requests, and feature attribution."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.artifact: dict[str, Any] | None = None
        self.pipeline: Pipeline | None = None
        self.model_version: str | None = None
        self.model_type: str | None = None
        self.default_threshold: float = 0.50
        self.explanation_service: ExplanationService | None = None

    def load_model(self, custom_path: Path | None = None) -> None:
        """Load and initialize model artifact and explanation services."""
        artifact_path = custom_path or self.settings.resolve_artifact_path()
        logger.info("Initializing PredictorService with artifact at: %s", artifact_path)

        self.artifact = load_model_artifact(artifact_path)
        self.pipeline = self.artifact["pipeline"]
        self.model_version = self.artifact["model_version"]
        self.model_type = self.artifact["model_type"]
        self.default_threshold = float(self.artifact.get("selected_threshold", 0.50))

        # Initialize explanation service
        self.explanation_service = ExplanationService(
            pipeline=self.pipeline,
            enabled=self.settings.ENABLE_SHAP_EXPLANATIONS,
        )
        logger.info(
            "PredictorService ready. Version: %s, Model: %s, Default Threshold: %.4f",
            self.model_version,
            self.model_type,
            self.default_threshold,
        )

    def is_ready(self) -> bool:
        """Check if pipeline is properly loaded and ready for inference."""
        return self.pipeline is not None and self.artifact is not None

    def _determine_threshold(self, request_threshold: float | None = None) -> float:
        """Determine applicable decision threshold honoring query override, env override, or artifact default."""
        if request_threshold is not None:
            return request_threshold
        if self.settings.DECISION_THRESHOLD_OVERRIDE is not None:
            return self.settings.DECISION_THRESHOLD_OVERRIDE
        return self.default_threshold

    def _categorize_risk(self, probability: float, score: float, threshold: float) -> RiskLevel:
        """Categorize risk level into LOW, MEDIUM, or HIGH.

        Transactions exceeding the decision threshold are categorized as HIGH risk.
        Transactions below threshold are banded into LOW (< 30) or MEDIUM (30-70).
        """
        if probability >= threshold or score >= self.settings.MEDIUM_RISK_MAX:
            return RiskLevel.HIGH
        elif score >= self.settings.LOW_RISK_MAX:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _transaction_to_dataframe(self, transaction: TransactionInput) -> pd.DataFrame:
        """Convert single transaction into a single-row DataFrame with strict feature order."""
        data = transaction.model_dump()
        ordered_data = {feat: [data[feat]] for feat in EXPECTED_FEATURE_ORDER}
        return pd.DataFrame(ordered_data)

    def predict_single(
        self,
        transaction: TransactionInput,
        threshold_override: float | None = None,
        include_explanation: bool = False,
    ) -> PredictionResponse | PredictionWithExplanationResponse:
        """Execute fraud inference on a single transaction."""
        if not self.is_ready():
            raise RuntimeError("Model pipeline is not loaded. Cannot process inference.")

        # Prepare ordered DataFrame
        df_row = self._transaction_to_dataframe(transaction)

        # Run inference
        probabilities = self.pipeline.predict_proba(df_row)
        fraud_proba = float(probabilities[0, 1])
        risk_score = round(fraud_proba * 100.0, 2)

        # Apply threshold
        threshold = self._determine_threshold(threshold_override)
        predicted_class = 1 if fraud_proba >= threshold else 0
        risk_level = self._categorize_risk(fraud_proba, risk_score, threshold)

        explanations = None
        if include_explanation and self.explanation_service is not None:
            explanations = self.explanation_service.explain_instance(df_row, top_k=5)

        if include_explanation:
            return PredictionWithExplanationResponse(
                fraud_probability=round(fraud_proba, 4),
                risk_score=risk_score,
                predicted_class=predicted_class,
                risk_level=risk_level,
                threshold=round(threshold, 4),
                model_version=str(self.model_version),
                top_risk_factors=explanations,
            )

        return PredictionResponse(
            fraud_probability=round(fraud_proba, 4),
            risk_score=risk_score,
            predicted_class=predicted_class,
            risk_level=risk_level,
            threshold=round(threshold, 4),
            model_version=str(self.model_version),
        )

    def predict_batch(
        self,
        batch_input: BatchTransactionInput,
        threshold_override: float | None = None,
    ) -> BatchPredictionResponse:
        """Execute batch inference on multiple transactions with bounded memory footprint."""
        if not self.is_ready():
            raise RuntimeError("Model pipeline is not loaded. Cannot process inference.")

        total_tx = len(batch_input.transactions)
        if total_tx > self.settings.MAX_BATCH_SIZE:
            raise ValueError(
                f"Batch size {total_tx} exceeds maximum permitted limit of {self.settings.MAX_BATCH_SIZE}."
            )

        # Construct batch DataFrame with guaranteed column order
        rows = [t.model_dump() for t in batch_input.transactions]
        batch_df = pd.DataFrame(rows)[EXPECTED_FEATURE_ORDER]

        probabilities = self.pipeline.predict_proba(batch_df)[:, 1]
        threshold = self._determine_threshold(threshold_override)

        predictions: list[PredictionResponse] = []
        flagged_count = 0

        for proba in probabilities:
            fraud_proba = float(proba)
            risk_score = round(fraud_proba * 100.0, 2)
            predicted_class = 1 if fraud_proba >= threshold else 0
            if predicted_class == 1:
                flagged_count += 1

            risk_level = self._categorize_risk(fraud_proba, risk_score, threshold)

            predictions.append(
                PredictionResponse(
                    fraud_probability=round(fraud_proba, 4),
                    risk_score=risk_score,
                    predicted_class=predicted_class,
                    risk_level=risk_level,
                    threshold=round(threshold, 4),
                    model_version=str(self.model_version),
                )
            )

        return BatchPredictionResponse(
            total_transactions=total_tx,
            flagged_fraud_count=flagged_count,
            model_version=str(self.model_version),
            predictions=predictions,
        )

    def get_model_info(self) -> ModelInfoResponse:
        """Return non-sensitive model metadata and validation metrics."""
        if not self.is_ready() or self.artifact is None:
            raise RuntimeError("Model artifact is not loaded.")

        return ModelInfoResponse(
            model_version=str(self.artifact.get("model_version", "unknown")),
            model_type=str(self.artifact.get("model_type", "unknown")),
            selected_threshold=float(self.artifact.get("selected_threshold", 0.5)),
            expected_features=list(
                self.artifact.get("expected_feature_order", EXPECTED_FEATURE_ORDER)
            ),
            training_dataset_description=str(self.artifact.get("training_dataset_description", "")),
            training_config=dict(self.artifact.get("training_config", {})),
            validation_metrics=dict(self.artifact.get("validation_metrics", {})),
            test_metrics=dict(self.artifact.get("test_metrics", {})),
        )


# Global singleton instance for application lifespan
predictor_service = PredictorService()
