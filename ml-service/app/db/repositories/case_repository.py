"""Repository for investigation case database operations and state transitions."""

from datetime import UTC, datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models.investigation_case import InvestigationCase
from app.db.models.prediction import Prediction
from app.db.models.transaction import Transaction

ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"IN_REVIEW", "CLOSED"},
    "IN_REVIEW": {"OPEN", "CONFIRMED_FRAUD", "LEGITIMATE"},
    "CONFIRMED_FRAUD": {"CLOSED"},
    "LEGITIMATE": {"CLOSED"},
    "CLOSED": set(),
}

VALID_STATUSES = set(ALLOWED_STATUS_TRANSITIONS.keys())


class CaseRepository:
    """Encapsulates database access and lifecycle state transitions for investigation cases."""

    @staticmethod
    def get_by_id(db: Session, case_id: int) -> InvestigationCase | None:
        """Fetch a single investigation case by its primary key with eager associations."""
        stmt = (
            select(InvestigationCase)
            .where(InvestigationCase.id == case_id)
            .options(
                selectinload(InvestigationCase.assigned_user),
                selectinload(InvestigationCase.case_notes),
                selectinload(InvestigationCase.transaction).selectinload(Transaction.predictions),
            )
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_by_transaction_id(db: Session, transaction_id: int) -> InvestigationCase | None:
        """Fetch investigation case for a given transaction ID."""
        stmt = (
            select(InvestigationCase)
            .where(InvestigationCase.transaction_id == transaction_id)
            .options(
                selectinload(InvestigationCase.assigned_user),
                selectinload(InvestigationCase.case_notes),
                selectinload(InvestigationCase.transaction).selectinload(Transaction.predictions),
            )
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def create(
        db: Session,
        transaction_id: int,
        description: str | None = None,
        assigned_user_id: int | None = None,
        assigned_to: str | None = None,
        notes: str | None = None,
    ) -> InvestigationCase:
        """Create a new investigation case in OPEN status."""
        case = InvestigationCase(
            transaction_id=transaction_id,
            status="OPEN",
            description=description,
            assigned_user_id=assigned_user_id,
            assigned_to=assigned_to,
            notes=notes,
        )
        db.add(case)
        db.flush()
        return case

    @staticmethod
    def list_cases(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        assigned_user_id: int | None = None,
        transaction_id: int | None = None,
        risk_level: str | None = None,
        predicted_class: int | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        visible_user_id: int | None = None,
        is_admin_or_auditor: bool = False,
    ) -> tuple[list[InvestigationCase], int]:
        """Retrieve paginated investigation cases with applicable filters and visibility rules."""
        stmt = select(InvestigationCase)

        # Visibility filtering for Analyst
        if not is_admin_or_auditor:
            if visible_user_id is not None:
                # Analyst can see cases assigned to them OR unassigned cases
                stmt = stmt.where(
                    (InvestigationCase.assigned_user_id == visible_user_id)
                    | (InvestigationCase.assigned_user_id.is_(None))
                )
            else:
                # Unauthenticated/restricted fallback: only unassigned
                stmt = stmt.where(InvestigationCase.assigned_user_id.is_(None))

        # Direct filters
        if status:
            stmt = stmt.where(InvestigationCase.status == status.upper())

        if assigned_user_id is not None:
            stmt = stmt.where(InvestigationCase.assigned_user_id == assigned_user_id)

        if transaction_id is not None:
            stmt = stmt.where(InvestigationCase.transaction_id == transaction_id)

        if created_from:
            stmt = stmt.where(InvestigationCase.created_at >= created_from)

        if created_to:
            stmt = stmt.where(InvestigationCase.created_at <= created_to)

        # Filters on latest prediction through transaction relationship
        if risk_level or predicted_class is not None:
            # Subquery to match transactions having matching latest predictions
            pred_filter = select(Prediction.transaction_id)
            if risk_level:
                pred_filter = pred_filter.where(Prediction.risk_level == risk_level.upper())
            if predicted_class is not None:
                pred_filter = pred_filter.where(Prediction.predicted_class == predicted_class)

            stmt = stmt.where(InvestigationCase.transaction_id.in_(pred_filter))

        # Total count query
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = db.execute(count_stmt).scalar_one()

        # Deterministic sorting: newest first, tie-break by ID
        stmt = (
            stmt.order_by(desc(InvestigationCase.created_at), desc(InvestigationCase.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .options(
                selectinload(InvestigationCase.assigned_user),
                selectinload(InvestigationCase.case_notes),
                selectinload(InvestigationCase.transaction).selectinload(Transaction.predictions),
            )
        )

        records = list(db.execute(stmt).scalars().all())
        return records, total_count

    @staticmethod
    def validate_status_transition(current_status: str, next_status: str) -> None:
        """Validate state transition rules against the state machine.

        Raises:
            ValueError: If the requested transition is illegal according to business rules.
        """
        curr = current_status.upper()
        target = next_status.upper()

        if target not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{next_status}'. Must be one of: {sorted(VALID_STATUSES)}")

        if curr == target:
            return  # No-op status update

        allowed = ALLOWED_STATUS_TRANSITIONS.get(curr, set())
        if target not in allowed:
            raise ValueError(
                f"Invalid status transition from '{curr}' to '{target}'. "
                f"Allowed target status(es): {sorted(allowed) if allowed else 'None (Terminal State)'}."
            )

    @staticmethod
    def update_status(
        case: InvestigationCase,
        new_status: str,
    ) -> tuple[str, str]:
        """Apply state transition and maintain resolution timestamp invariants.

        Returns:
            Tuple of (old_status, new_status).
        """
        old_status = case.status
        target_status = new_status.upper()

        if old_status == target_status:
            return old_status, target_status

        CaseRepository.validate_status_transition(old_status, target_status)

        case.status = target_status
        now_utc = datetime.now(UTC)
        case.updated_at = now_utc

        # Handle resolution timestamp behavior
        if target_status in {"CONFIRMED_FRAUD", "LEGITIMATE"}:
            case.resolved_at = now_utc
        elif target_status == "CLOSED":
            if case.resolved_at is None:
                case.resolved_at = now_utc
        elif target_status == "OPEN" and old_status == "IN_REVIEW":
            # Reopening or moving back to unreviewed: clear resolution timestamp
            case.resolved_at = None

        return old_status, target_status
