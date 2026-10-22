"""Pydantic V2 schemas for prediction responses, health checks, and model metadata."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RiskLevel(StrEnum):
    """Transaction risk categorization."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class FeatureAttribution(BaseModel):
    """SHAP feature attribution explaining a feature's push on the risk score."""

    feature: str = Field(..., description="Feature name (e.g., V14, Amount)")
    attribution: float = Field(..., description="SHAP value contribution toward fraud probability")
    value: float = Field(..., description="Actual feature value in the request")


class PredictionResponse(BaseModel):
    """Inference response structure."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fraud_probability": 0.8245,
                "risk_score": 82.45,
                "predicted_class": 1,
                "risk_level": "HIGH",
                "threshold": 0.56,
                "model_version": "fraud-model-v1",
                "disclaimer": "Predictions represent estimated probabilistic risk score and do not constitute absolute determination of fraud.",
            }
        }
    )

    fraud_probability: float = Field(
        ...,
        description="Predicted probability that transaction is fraudulent [0.0 - 1.0]",
        ge=0.0,
        le=1.0,
    )
    risk_score: float = Field(
        ...,
        description="Normalized risk score from 0.0 to 100.0",
        ge=0.0,
        le=100.0,
    )
    predicted_class: int = Field(
        ...,
        description="Binary decision flag: 1 = Flagged Fraud Risk, 0 = Legitimate",
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Risk category based on calibrated thresholds (LOW, MEDIUM, HIGH)",
    )
    threshold: float = Field(
        ...,
        description="Decision threshold applied for positive fraud classification",
    )
    model_version: str = Field(
        ...,
        description="Model artifact version used for inference",
    )
    disclaimer: str = Field(
        default="Predictions represent estimated probabilistic risk score and do not constitute absolute determination of fraud.",
        description="Operational notice on ML estimation scope",
    )


class PredictionWithExplanationResponse(PredictionResponse):
    """Inference response enriched with top contributing feature explanations."""

    top_risk_factors: list[FeatureAttribution] | None = Field(
        default=None,
        description="Top features increasing or decreasing the fraud probability (via SHAP)",
    )


class BatchPredictionResponse(BaseModel):
    """Batch prediction results wrapper."""

    total_transactions: int = Field(..., description="Total transactions evaluated in batch")
    flagged_fraud_count: int = Field(..., description="Count of transactions flagged as fraud risk")
    model_version: str = Field(..., description="Model version used for batch evaluation")
    predictions: list[PredictionResponse] = Field(
        ..., description="Ordered list of transaction predictions"
    )


class HealthResponse(BaseModel):
    """Health check status response."""

    status: str = Field(
        ..., description="Service overall health ('healthy', 'degraded', 'unavailable')"
    )
    model_loaded: bool = Field(
        ..., description="True if ML pipeline artifact is safely loaded in memory"
    )
    model_version: str | None = Field(None, description="Active model version identifier")
    model_type: str | None = Field(None, description="Active classifier architecture")
    environment: str = Field(..., description="Current deployment environment")


class ModelInfoResponse(BaseModel):
    """Metadata response describing active model artifact without exposing secrets or paths."""

    model_version: str = Field(..., description="Artifact version string")
    model_type: str = Field(..., description="Classifier algorithm name")
    selected_threshold: float = Field(..., description="Optimized decision threshold")
    expected_features: list[str] = Field(
        ..., description="Ordered feature inputs expected by model"
    )
    training_dataset_description: str = Field(..., description="Summary of dataset and splits used")
    training_config: dict[str, Any] = Field(
        ..., description="Hyperparameters and pipeline configuration"
    )
    validation_metrics: dict[str, Any] = Field(
        ..., description="Validation partition performance metrics"
    )
    test_metrics: dict[str, Any] = Field(
        ..., description="Final test partition performance metrics"
    )
    risk_categories: dict[str, str] = Field(
        default={
            "LOW": "Score < 30.0 (Minimal risk, standard automated processing)",
            "MEDIUM": "Score 30.0 to 70.0 (Elevated risk, recommended secondary verification)",
            "HIGH": "Score >= 70.0 or above decision threshold (Actionable risk, flag for review/block)",
        },
        description="Operational definition of risk levels",
    )
