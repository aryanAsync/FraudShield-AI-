"""API endpoints for immutable security and administrative audit logs."""

import logging
import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin_or_auditor
from app.db.models.user import User
from app.db.repositories.audit_log_repository import AuditLogRepository
from app.db.session import get_db
from app.schemas.audit import AuditLogResponse, PaginatedAuditLogsResponse

logger = logging.getLogger("audit_routes")

router = APIRouter(prefix="/api/v1/audit-logs", tags=["Audit Trail"])


@router.get(
    "",
    response_model=PaginatedAuditLogsResponse,
    summary="Query system audit log trail",
    description=(
        "Returns paginated immutable audit logs with optional filters and deterministic ordering. "
        "Strictly accessible only to ADMIN and AUDITOR roles. Read-only."
    ),
    responses={
        400: {"description": "Invalid date range or parameters."},
        403: {"description": "Insufficient permissions (Analyst forbidden)."},
    },
)
def list_audit_logs(
    page: int = Query(default=1, ge=1, description="Page index (1-based)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    actor_id: str | None = Query(default=None, description="Filter by actor ID"),
    action: str | None = Query(default=None, description="Filter by action name (e.g., CASE_CREATED, LOGIN_SUCCESS)"),
    entity_type: str | None = Query(default=None, description="Filter by entity type (e.g., investigation_case, user)"),
    entity_id: str | None = Query(default=None, description="Filter by entity identifier"),
    created_from: datetime | None = Query(default=None, description="Earliest event timestamp filter"),
    created_to: datetime | None = Query(default=None, description="Latest event timestamp filter"),
    current_user: User = Depends(require_admin_or_auditor),
    db: Session = Depends(get_db),
) -> PaginatedAuditLogsResponse:
    """Retrieve paginated audit logs with deterministic ordering."""
    if created_from and created_to and created_from > created_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date range: 'created_from' cannot be later than 'created_to'.",
        )

    records, total_count = AuditLogRepository.list_logs(
        db=db,
        page=page,
        page_size=page_size,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        created_from=created_from,
        created_to=created_to,
    )

    items = [
        AuditLogResponse(
            id=log.id,
            actor_id=log.actor_id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            details=log.details,
            created_at=log.created_at,
        )
        for log in records
    ]
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

    return PaginatedAuditLogsResponse(
        items=items,
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
