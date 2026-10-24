"""Pydantic V2 schemas for investigation case notes."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CaseNoteCreateRequest(BaseModel):
    """Payload to add a chronological investigation note to a case."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "body": "Reviewed transaction details, confirmed with cardholder via phone, escalated for chargeback review."
            }
        },
    )

    body: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Investigation findings, evidence summary, and notes",
    )


class CaseNoteResponse(BaseModel):
    """Investigation note response representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique note identifier")
    case_id: int = Field(..., description="Associated investigation case identifier")
    author_id: int | None = Field(None, description="Author user ID (nullable if user deleted)")
    author_name: str = Field(..., description="Display name of author")
    author_email: str = Field(..., description="Email address of author")
    author_role: str = Field(..., description="RBAC role of author at creation time")
    body: str = Field(..., description="Note text content")
    created_at: datetime = Field(..., description="Timezone-aware creation timestamp")


class PaginatedCaseNotesResponse(BaseModel):
    """Paginated collection of case notes."""

    items: list[CaseNoteResponse] = Field(..., description="List of notes in chronological order")
    total: int = Field(..., description="Total notes count for this case")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total pages available")
