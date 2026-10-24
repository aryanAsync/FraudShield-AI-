"""Pydantic V2 schemas for investigation cases, assignments, and state transitions."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.case_note import CaseNoteResponse


class CaseCreateRequest(BaseModel):
    """Payload to open an investigation case for a transaction."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "transaction_id": 1,
                "description": "High risk transaction flagged by Random Forest model for manual review.",
            }
        },
    )

    transaction_id: int = Field(..., ge=1, description="ID of the transaction to investigate")
    description: str | None = Field(
        None, max_length=2000, description="Optional opening summary or notes"
    )


class CaseUpdateRequest(BaseModel):
    """Payload to update an investigation case."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "status": "IN_REVIEW",
                "assigned_user_id": 2,
                "description": "Updated case description.",
            }
        },
    )

    status: str | None = Field(
        None,
        description="Target status: OPEN, IN_REVIEW, CONFIRMED_FRAUD, LEGITIMATE, or CLOSED",
    )
    assigned_user_id: int | None = Field(
        None,
        description="User ID of active analyst to assign (or null to unassign if permitted)",
    )
    description: str | None = Field(
        None, max_length=2000, description="Updated case summary description"
    )


class CaseAssignedUserResponse(BaseModel):
    """Public summary of the assigned analyst."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="User ID")
    name: str = Field(..., description="Full display name")
    email: str = Field(..., description="User email address")
    role: str = Field(..., description="User role")


class CaseTransactionSummary(BaseModel):
    """Summary of the transaction under investigation."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Transaction ID")
    amount: float = Field(..., description="Transaction amount")
    transaction_time: float = Field(..., description="Time elapsed in seconds")
    external_reference: str | None = Field(None, description="External reference ID")
    submitted_by: str | None = Field(None, description="Submitter ID or email")
    created_at: datetime = Field(..., description="Timezone-aware creation timestamp")


class CasePredictionSummary(BaseModel):
    """Summary of the latest prediction outcome for the transaction under investigation."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Prediction ID")
    risk_score: float = Field(..., description="Calibrated risk score (0-100)")
    fraud_probability: float = Field(..., description="Fraud probability (0.0 - 1.0)")
    predicted_class: int = Field(..., description="Binary prediction (0=Legit, 1=Fraud)")
    risk_level: str = Field(..., description="Risk tier (LOW, MEDIUM, HIGH)")
    decision_threshold: float = Field(..., description="Applied decision threshold")
    model_version: str = Field(..., description="Model version")
    predicted_at: datetime = Field(..., description="Inference timestamp")


class CaseResponse(BaseModel):
    """Standard representation of an investigation case."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Case identifier")
    transaction_id: int = Field(..., description="Transaction ID under investigation")
    status: str = Field(..., description="Current status: OPEN, IN_REVIEW, CONFIRMED_FRAUD, LEGITIMATE, or CLOSED")
    assigned_user_id: int | None = Field(None, description="Assigned analyst user ID")
    assigned_to: str | None = Field(None, description="Assigned analyst username/email")
    description: str | None = Field(None, description="Case description or opening notes")
    notes: str | None = Field(None, description="Legacy free-text notes")
    created_at: datetime = Field(..., description="Case opening timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    resolved_at: datetime | None = Field(None, description="Case resolution/closure timestamp")

    # Associated nested entities
    assigned_user: CaseAssignedUserResponse | None = Field(None, description="Assigned analyst profile")
    transaction: CaseTransactionSummary | None = Field(None, description="Associated transaction summary")
    latest_prediction: CasePredictionSummary | None = Field(None, description="Latest model prediction summary")


class CaseDetailResponse(CaseResponse):
    """Detailed case representation including full chronological notes timeline."""

    case_notes: list[CaseNoteResponse] = Field(
        default_factory=list, description="Chronological list of investigation notes"
    )


class PaginatedCasesResponse(BaseModel):
    """Paginated collection of investigation cases."""

    items: list[CaseResponse] = Field(..., description="List of investigation cases")
    total: int = Field(..., description="Total matching cases count")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total available pages")
