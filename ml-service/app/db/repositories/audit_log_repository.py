"""Repository for security and business audit trail logging and queries."""

from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog


class AuditLogRepository:
    """Encapsulates append-only operations and filtered queries for system audit records."""

    @staticmethod
    def create(
        db: Session,
        action: str,
        entity_type: str,
        entity_id: str,
        actor_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Create and persist an immutable audit log entry."""
        log = AuditLog(
            actor_id=actor_id,
            action=action.upper(),
            entity_type=entity_type.lower(),
            entity_id=str(entity_id),
            details=details,
        )
        db.add(log)
        db.flush()
        return log

    @staticmethod
    def get_by_id(db: Session, audit_id: int) -> AuditLog | None:
        """Retrieve an audit log entry by primary key."""
        stmt = select(AuditLog).where(AuditLog.id == audit_id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_logs(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        actor_id: str | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[AuditLog], int]:
        """Query paginated audit logs with optional filters and deterministic ordering."""
        stmt = select(AuditLog)

        if actor_id:
            stmt = stmt.where(AuditLog.actor_id == actor_id)

        if action:
            stmt = stmt.where(AuditLog.action == action.upper())

        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type.lower())

        if entity_id:
            stmt = stmt.where(AuditLog.entity_id == str(entity_id))

        if created_from:
            stmt = stmt.where(AuditLog.created_at >= created_from)

        if created_to:
            stmt = stmt.where(AuditLog.created_at <= created_to)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = db.execute(count_stmt).scalar_one()

        # Deterministic ordering: newest first, tie-break by ID
        stmt = (
            stmt.order_by(desc(AuditLog.created_at), desc(AuditLog.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        records = list(db.execute(stmt).scalars().all())
        return records, total_count
