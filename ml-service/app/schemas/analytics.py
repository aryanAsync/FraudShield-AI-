"""Pydantic schemas for dashboard analytics, risk distributions, and trend metrics."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsFilterSummary(BaseModel):
    """Echoes applied timestamp filter bounds."""

    start_date: datetime | None = Field(default=None, description="Start date filter (UTC)")
    end_date: datetime | None = Field(default=None, description="End date filter (UTC)")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Overview Schemas
# ---------------------------------------------------------------------------


class OverviewTransactionsSummary(BaseModel):
    """Transaction volume and fraud classification metrics."""

    total_transactions: int = Field(..., description="Total distinct transaction records")
    transactions_with_predictions: int = Field(
        ..., description="Distinct transactions evaluated with at least one prediction"
    )
    predicted_fraud_count: int = Field(
        ..., description="Distinct transactions whose latest prediction flagged fraud (predicted_class = 1)"
    )
    predicted_legitimate_count: int = Field(
        ..., description="Distinct transactions whose latest prediction flagged legitimate (predicted_class = 0)"
    )
    predicted_fraud_percentage: float = Field(
        ..., description="Percentage of evaluated transactions predicted as fraud [0.0 - 100.0]"
    )


class OverviewPredictionsSummary(BaseModel):
    """Inference evaluation volume metrics."""

    total_predictions: int = Field(..., description="Total inference evaluation executions in scope")


class OverviewRiskSummary(BaseModel):
    """Aggregate risk score and categorical tier distribution."""

    average_risk_score: float = Field(
        ..., description="Average latest risk score across evaluated transactions [0.0 - 100.0]"
    )
    average_fraud_probability: float = Field(
        ..., description="Average latest calibrated fraud probability [0.0 - 1.0]"
    )
    high_risk_transactions: int = Field(
        ..., description="Transactions whose latest prediction is classified HIGH risk"
    )
    medium_risk_transactions: int = Field(
        ..., description="Transactions whose latest prediction is classified MEDIUM risk"
    )
    low_risk_transactions: int = Field(
        ..., description="Transactions whose latest prediction is classified LOW risk"
    )


class OverviewCasesSummary(BaseModel):
    """Triage investigation case counts and outcome breakdown."""

    total_cases: int = Field(..., description="Total investigation cases matching filters")
    open: int = Field(..., description="Cases currently in OPEN status awaiting review")
    in_review: int = Field(..., description="Cases currently actively IN_REVIEW by an analyst")
    confirmed_fraud: int = Field(..., description="Cases adjudicated as CONFIRMED_FRAUD")
    legitimate: int = Field(..., description="Cases adjudicated as LEGITIMATE (false alarms)")
    closed: int = Field(..., description="Cases archived in terminal CLOSED status")
    unresolved: int = Field(..., description="Total pending unresolved cases (OPEN + IN_REVIEW)")
    resolved: int = Field(..., description="Total finalized cases (CONFIRMED_FRAUD + LEGITIMATE + CLOSED)")


class AnalyticsOverviewResponse(BaseModel):
    """Comprehensive high-level KPI dashboard overview."""

    filters: AnalyticsFilterSummary
    transactions: OverviewTransactionsSummary
    predictions: OverviewPredictionsSummary
    risk: OverviewRiskSummary
    cases: OverviewCasesSummary

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Risk Distribution Schemas
# ---------------------------------------------------------------------------


class RiskDistributionItem(BaseModel):
    """Categorical risk tier breakdown item."""

    risk_level: str = Field(..., description="Risk category: LOW, MEDIUM, or HIGH")
    count: int = Field(..., description="Number of distinct transactions at this risk tier")
    percentage: float = Field(
        ..., description="Percentage of evaluated transactions belonging to this tier [0.0 - 100.0]"
    )


class ClassificationDistributionSummary(BaseModel):
    """Binary model classification breakdown for evaluated transactions."""

    predicted_fraud_count: int = Field(..., description="Transactions with latest predicted_class = 1")
    predicted_fraud_percentage: float = Field(..., description="Percentage of transactions predicted as fraud")
    predicted_legitimate_count: int = Field(..., description="Transactions with latest predicted_class = 0")
    predicted_legitimate_percentage: float = Field(..., description="Percentage of transactions predicted as legitimate")


class RiskDistributionResponse(BaseModel):
    """Current risk distribution breakdown across all evaluated transactions."""

    total_transactions: int = Field(..., description="Total distinct transactions with predictions")
    items: list[RiskDistributionItem] = Field(..., description="Risk tier counts and percentages")
    classification: ClassificationDistributionSummary = Field(
        ..., description="Model classification binary breakdown"
    )

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Time-Series Trends Schemas
# ---------------------------------------------------------------------------


class TrendBucketItem(BaseModel):
    """Time-series metrics aggregated for a specific time bucket."""

    timestamp: datetime = Field(..., description="Bucket start timestamp (UTC)")
    prediction_count: int = Field(..., description="Total prediction events in bucket")
    distinct_transactions: int = Field(..., description="Distinct transactions evaluated in bucket")
    predicted_fraud_count: int = Field(..., description="Predictions classified as fraud in bucket")
    predicted_legitimate_count: int = Field(..., description="Predictions classified as legitimate in bucket")
    high_risk_count: int = Field(..., description="Predictions classified as HIGH risk in bucket")
    average_risk_score: float = Field(..., description="Average risk score in bucket [0.0 - 100.0]")


class AnalyticsTrendsResponse(BaseModel):
    """Time-series trend metrics over specified interval buckets."""

    interval: str = Field(..., description="Aggregation interval: 'hour' or 'day'")
    metrics: dict[str, str] = Field(..., description="Metadata describing event timestamp field")
    items: list[TrendBucketItem] = Field(..., description="Chronological time buckets")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Case Status Distribution Schemas
# ---------------------------------------------------------------------------


class CaseStatusDistributionItem(BaseModel):
    """Investigation case status metric item."""

    status: str = Field(..., description="Investigation status name")
    count: int = Field(..., description="Number of cases in this status")
    percentage: float = Field(..., description="Percentage of total cases in this status [0.0 - 100.0]")


class CaseStatusSummary(BaseModel):
    """Operational workload and resolution timing summary."""

    assigned_count: int = Field(..., description="Cases currently assigned to an analyst")
    unassigned_count: int = Field(..., description="Cases in queue not yet assigned")
    unresolved_count: int = Field(..., description="Cases in OPEN or IN_REVIEW status")
    resolved_fraud_count: int = Field(..., description="Cases confirmed as fraudulent")
    resolved_legitimate_count: int = Field(..., description="Cases cleared as legitimate")
    average_resolution_time_seconds: float | None = Field(
        default=None, description="Average seconds from creation to resolution for resolved cases"
    )


class CaseStatusDistributionResponse(BaseModel):
    """Investigation case workflow status breakdown."""

    total_cases: int = Field(..., description="Total investigation cases in scope")
    items: list[CaseStatusDistributionItem] = Field(..., description="Case counts and shares by status")
    summary: CaseStatusSummary = Field(..., description="Operational metrics and assignment status")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Feature Importance Schemas (Aggregated Model Explanations)
# ---------------------------------------------------------------------------


class FeatureImportanceItem(BaseModel):
    """Aggregated SHAP feature attribution contribution item."""

    rank: int = Field(..., description="Importance rank (1 is highest impact)")
    feature: str = Field(..., description="Feature name (e.g., V14, Amount, V10)")
    mean_absolute_attribution: float = Field(
        ..., description="Mean absolute SHAP attribution contribution across sample"
    )
    sample_count: int = Field(..., description="Number of prediction explanations contributing to this metric")


class FeatureImportanceResponse(BaseModel):
    """Aggregated SHAP model explanation insights for high-risk transactions."""

    sample_size: int = Field(..., description="Number of prediction explanation records evaluated")
    target_risk_level: str | None = Field(
        default=None, description="Risk level filter applied for explanation aggregation"
    )
    features: list[FeatureImportanceItem] = Field(
        ..., description="Top contributing features ranked by mean absolute impact"
    )
    disclaimer: str = Field(
        default=(
            "SHAP feature attributions describe model input contributions for this sample; "
            "features V1-V28 are anonymized PCA components and do not indicate specific real-world "
            "identity, location, or customer attributes."
        ),
        description="AI governance and regulatory interpretation disclaimer",
    )

    model_config = ConfigDict(from_attributes=True)
