"""Pydantic V2 schemas for audit trail events and read queries."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    """Audit log entry response representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique audit event ID")
    actor_id: str | None = Field(None, description="Actor ID who triggered the action")
    action: str = Field(..., description="Action name (e.g., CASE_CREATED, CASE_STATUS_CHANGED)")
    entity_type: str = Field(..., description="Target entity type (e.g., case, transaction, user)")
    entity_id: str = Field(..., description="Identifier of the target entity")
    details: dict[str, Any] | None = Field(None, description="Structured event metadata or delta")
    created_at: datetime = Field(..., description="Timezone-aware creation timestamp")


class PaginatedAuditLogsResponse(BaseModel):
    """Paginated collection of audit log entries."""

    items: list[AuditLogResponse] = Field(..., description="List of audit log records")
    total: int = Field(..., description="Total matching logs count")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total available pages")
