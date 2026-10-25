"""Pydantic V2 schemas for transaction persistence, scoring, and history APIs."""

import math
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.prediction import FeatureAttribution, RiskLevel


class ScoreTransactionRequest(BaseModel):
    """Payload for scoring and persisting a new transaction."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "Time": 406.0,
                "V1": -2.312,
                "V2": 1.951,
                "V3": -1.609,
                "V4": 3.997,
                "V5": -0.522,
                "V6": -1.426,
                "V7": -2.537,
                "V8": 1.391,
                "V9": -2.770,
                "V10": -2.772,
                "V11": 3.202,
                "V12": -2.899,
                "V13": -0.595,
                "V14": -4.289,
                "V15": 0.389,
                "V16": -1.140,
                "V17": -2.830,
                "V18": -0.016,
                "V19": 0.416,
                "V20": 0.126,
                "V21": 0.517,
                "V22": -0.035,
                "V23": -0.465,
                "V24": 0.320,
                "V25": 0.044,
                "V26": 0.177,
                "V27": 0.261,
                "V28": -0.143,
                "Amount": 149.99,
                "external_reference": "TXN-984321",
                "explain": True,
            }
        },
    )

    Time: float = Field(..., description="Seconds elapsed since the first transaction in dataset")
    V1: float = Field(..., description="PCA feature V1")
    V2: float = Field(..., description="PCA feature V2")
    V3: float = Field(..., description="PCA feature V3")
    V4: float = Field(..., description="PCA feature V4")
    V5: float = Field(..., description="PCA feature V5")
    V6: float = Field(..., description="PCA feature V6")
    V7: float = Field(..., description="PCA feature V7")
    V8: float = Field(..., description="PCA feature V8")
    V9: float = Field(..., description="PCA feature V9")
    V10: float = Field(..., description="PCA feature V10")
    V11: float = Field(..., description="PCA feature V11")
    V12: float = Field(..., description="PCA feature V12")
    V13: float = Field(..., description="PCA feature V13")
    V14: float = Field(..., description="PCA feature V14")
    V15: float = Field(..., description="PCA feature V15")
    V16: float = Field(..., description="PCA feature V16")
    V17: float = Field(..., description="PCA feature V17")
    V18: float = Field(..., description="PCA feature V18")
    V19: float = Field(..., description="PCA feature V19")
    V20: float = Field(..., description="PCA feature V20")
    V21: float = Field(..., description="PCA feature V21")
    V22: float = Field(..., description="PCA feature V22")
    V23: float = Field(..., description="PCA feature V23")
    V24: float = Field(..., description="PCA feature V24")
    V25: float = Field(..., description="PCA feature V25")
    V26: float = Field(..., description="PCA feature V26")
    V27: float = Field(..., description="PCA feature V27")
    V28: float = Field(..., description="PCA feature V28")
    Amount: float = Field(..., description="Transaction amount in currency units", ge=0.0)

    external_reference: str | None = Field(
        default=None,
        max_length=100,
        description="Optional unique client reference or idempotency key",
    )
    submitted_by: str | None = Field(
        default=None,
        max_length=100,
        description="Optional submitting entity or user, reserved for authentication phase",
    )
    explain: bool = Field(
        default=False,
        description="Whether to generate and persist SHAP feature attribution explanations",
    )
    threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional inference decision threshold override",
    )

    @field_validator("*", mode="after")
    @classmethod
    def check_finite(cls, v: Any) -> Any:
        """Reject NaN, inf, and -inf values."""
        if isinstance(v, (int, float)):
            if not math.isfinite(v):
                raise ValueError("Values must be finite numbers (NaN, inf, and -inf are rejected)")
        return v


class PredictionRecordResponse(BaseModel):
    """Persisted prediction record schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique prediction identifier")
    transaction_id: int = Field(..., description="Referenced transaction identifier")
    fraud_probability: float = Field(..., description="Fraud probability [0.0 - 1.0]")
    risk_score: float = Field(..., description="Normalized risk score [0.0 - 100.0]")
    predicted_class: int = Field(..., description="Binary decision (1=Fraud, 0=Legitimate)")
    risk_level: RiskLevel = Field(..., description="Categorical risk tier (LOW, MEDIUM, HIGH)")
    decision_threshold: float = Field(..., description="Threshold applied during evaluation")
    model_version: str = Field(..., description="Model artifact version")
    explanation: list[dict[str, Any]] | list[FeatureAttribution] | None = Field(
        default=None, description="Feature attribution attributions if requested"
    )
    predicted_at: datetime = Field(..., description="Timestamp of inference")


class ScoreTransactionResponse(BaseModel):
    """Response returned upon successfully scoring and persisting a transaction."""

    model_config = ConfigDict(from_attributes=True)

    transaction_id: int = Field(..., description="Persisted transaction identifier")
    external_reference: str | None = Field(None, description="External reference if supplied")
    transaction_time: float = Field(..., description="Transaction dataset time")
    amount: float = Field(..., description="Transaction amount")
    submitted_by: str | None = Field(None, description="Submitting user/service account")
    created_at: datetime = Field(..., description="Transaction creation timestamp")
    prediction: PredictionRecordResponse = Field(..., description="Persisted prediction result")


class TransactionSummaryResponse(BaseModel):
    """Summary of a transaction with its latest prediction for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Transaction ID")
    external_reference: str | None = Field(None, description="External reference key")
    transaction_time: float = Field(..., description="Transaction dataset time")
    amount: float = Field(..., description="Transaction amount")
    submitted_by: str | None = Field(None, description="Submitting entity")
    created_at: datetime = Field(..., description="Creation timestamp")
    latest_prediction: PredictionRecordResponse | None = Field(
        None, description="Most recent prediction result"
    )


class TransactionDetailResponse(BaseModel):
    """Detailed transaction response including anonymized PCA features and prediction summary."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Transaction ID")
    external_reference: str | None = Field(None, description="External reference key")
    transaction_time: float = Field(..., description="Transaction dataset time")
    amount: float = Field(..., description="Transaction amount")
    features: dict[str, float] = Field(..., description="Validated feature vector (V1 through V28)")
    submitted_by: str | None = Field(None, description="Submitting entity")
    created_at: datetime = Field(..., description="Creation timestamp")
    latest_prediction: PredictionRecordResponse | None = Field(
        None, description="Most recent prediction result"
    )
    predictions_count: int = Field(
        ..., description="Total number of prediction evaluations recorded"
    )


class PaginatedTransactionsResponse(BaseModel):
    """Paginated collection of transactions."""

    items: list[TransactionSummaryResponse] = Field(..., description="Transactions in current page")
    total: int = Field(..., description="Total matching transactions")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Page size limit")
    total_pages: int = Field(..., description="Total number of pages")


class PredictionHistoryResponse(BaseModel):
    """Collection of all prediction evaluations recorded for a specific transaction."""

    transaction_id: int = Field(..., description="Target transaction ID")
    total_evaluations: int = Field(..., description="Total predictions recorded")
    predictions: list[PredictionRecordResponse] = Field(
        ..., description="Historical predictions ordered newest first"
    )


class BatchScoreTransactionItem(BaseModel):
    """Single transaction record within a batch scoring request."""

    model_config = ConfigDict(extra="forbid")

    Time: float = Field(..., description="Seconds elapsed since the first transaction in dataset")
    V1: float = Field(..., description="PCA feature V1")
    V2: float = Field(..., description="PCA feature V2")
    V3: float = Field(..., description="PCA feature V3")
    V4: float = Field(..., description="PCA feature V4")
    V5: float = Field(..., description="PCA feature V5")
    V6: float = Field(..., description="PCA feature V6")
    V7: float = Field(..., description="PCA feature V7")
    V8: float = Field(..., description="PCA feature V8")
    V9: float = Field(..., description="PCA feature V9")
    V10: float = Field(..., description="PCA feature V10")
    V11: float = Field(..., description="PCA feature V11")
    V12: float = Field(..., description="PCA feature V12")
    V13: float = Field(..., description="PCA feature V13")
    V14: float = Field(..., description="PCA feature V14")
    V15: float = Field(..., description="PCA feature V15")
    V16: float = Field(..., description="PCA feature V16")
    V17: float = Field(..., description="PCA feature V17")
    V18: float = Field(..., description="PCA feature V18")
    V19: float = Field(..., description="PCA feature V19")
    V20: float = Field(..., description="PCA feature V20")
    V21: float = Field(..., description="PCA feature V21")
    V22: float = Field(..., description="PCA feature V22")
    V23: float = Field(..., description="PCA feature V23")
    V24: float = Field(..., description="PCA feature V24")
    V25: float = Field(..., description="PCA feature V25")
    V26: float = Field(..., description="PCA feature V26")
    V27: float = Field(..., description="PCA feature V27")
    V28: float = Field(..., description="PCA feature V28")
    Amount: float = Field(..., description="Transaction amount in currency units", ge=0.0)
    external_reference: str | None = Field(
        default=None,
        max_length=100,
        description="Optional unique client reference or idempotency key",
    )

    @field_validator("*", mode="after")
    @classmethod
    def check_finite(cls, v: Any) -> Any:
        """Reject NaN, inf, and -inf values."""
        if isinstance(v, (int, float)):
            if not math.isfinite(v):
                raise ValueError("Values must be finite numbers (NaN, inf, and -inf are rejected)")
        return v


class BatchScoreTransactionRequest(BaseModel):
    """Payload for submitting a batch of transactions for ML fraud scoring and persistence."""

    transactions: list[BatchScoreTransactionItem] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="List of transactions to score (max 1,000 per batch)",
    )
    threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional decision threshold override for this batch",
    )
    explain: bool = Field(
        default=False,
        description="Whether to generate SHAP explanations for high-risk transactions (slower)",
    )


class BatchScoreTransactionResponse(BaseModel):
    """Response returned upon successfully scoring and persisting a batch of transactions."""

    total_received: int = Field(..., description="Total transactions submitted in the request")
    persisted_count: int = Field(..., description="Number of transactions successfully persisted")
    flagged_fraud_count: int = Field(..., description="Number of transactions classified as fraud (class 1)")
    low_risk_count: int = Field(..., description="Number of transactions classified as LOW risk")
    medium_risk_count: int = Field(..., description="Number of transactions classified as MEDIUM risk")
    high_risk_count: int = Field(..., description="Number of transactions classified as HIGH risk")
    created_transaction_ids: list[int] = Field(..., description="IDs of newly created transaction records")
