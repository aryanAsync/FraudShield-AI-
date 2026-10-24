"""API endpoints for fraud investigation cases, state machine, assignments, and notes."""

import logging
import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    require_analyst_or_admin,
    require_any_authenticated,
)
from app.db.models.investigation_case import InvestigationCase
from app.db.models.user import User
from app.db.repositories.audit_log_repository import AuditLogRepository
from app.db.repositories.case_note_repository import CaseNoteRepository
from app.db.repositories.case_repository import CaseRepository
from app.db.repositories.transaction_repository import TransactionRepository
from app.db.repositories.user_repository import UserRepository
from app.db.session import get_db
from app.schemas.case import (
    CaseAssignedUserResponse,
    CaseCreateRequest,
    CaseDetailResponse,
    CasePredictionSummary,
    CaseResponse,
    CaseTransactionSummary,
    CaseUpdateRequest,
    PaginatedCasesResponse,
)
from app.schemas.case_note import (
    CaseNoteCreateRequest,
    CaseNoteResponse,
    PaginatedCaseNotesResponse,
)

logger = logging.getLogger("case_routes")

router = APIRouter(prefix="/api/v1/cases", tags=["Investigation Cases"])


def _to_case_response(case: InvestigationCase) -> CaseResponse:
    """Format SQLAlchemy InvestigationCase model into Pydantic schema."""
    assigned_user_dto = None
    if case.assigned_user:
        assigned_user_dto = CaseAssignedUserResponse(
            id=case.assigned_user.id,
            name=case.assigned_user.name,
            email=case.assigned_user.email,
            role=case.assigned_user.role,
        )

    tx_dto = None
    pred_dto = None
    if case.transaction:
        tx_dto = CaseTransactionSummary(
            id=case.transaction.id,
            amount=case.transaction.amount,
            transaction_time=case.transaction.transaction_time,
            external_reference=case.transaction.external_reference,
            submitted_by=case.transaction.submitted_by,
            created_at=case.transaction.created_at,
        )
        if case.transaction.predictions:
            latest = case.transaction.predictions[0]
            pred_dto = CasePredictionSummary(
                id=latest.id,
                risk_score=latest.risk_score,
                fraud_probability=latest.fraud_probability,
                predicted_class=latest.predicted_class,
                risk_level=latest.risk_level,
                decision_threshold=latest.decision_threshold,
                model_version=latest.model_version,
                predicted_at=latest.predicted_at,
            )

    return CaseResponse(
        id=case.id,
        transaction_id=case.transaction_id,
        status=case.status,
        assigned_user_id=case.assigned_user_id,
        assigned_to=case.assigned_to,
        description=case.description,
        notes=case.notes,
        created_at=case.created_at,
        updated_at=case.updated_at,
        resolved_at=case.resolved_at,
        assigned_user=assigned_user_dto,
        transaction=tx_dto,
        latest_prediction=pred_dto,
    )


def _to_case_detail_response(case: InvestigationCase) -> CaseDetailResponse:
    """Format full case details including chronological investigation notes."""
    base_dto = _to_case_response(case)
    notes_dto = [
        CaseNoteResponse(
            id=note.id,
            case_id=note.case_id,
            author_id=note.author_id,
            author_name=note.author_name,
            author_email=note.author_email,
            author_role=note.author_role,
            body=note.body,
            created_at=note.created_at,
        )
        for note in case.case_notes
    ]
    return CaseDetailResponse(
        **base_dto.model_dump(),
        case_notes=notes_dto,
    )


@router.post(
    "",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Open an investigation case for a transaction",
    description="Creates an investigation case in OPEN status. Requires ANALYST or ADMIN role.",
    responses={
        201: {"description": "Case opened successfully."},
        403: {"description": "Insufficient permissions (Auditor denied)."},
        404: {"description": "Transaction does not exist."},
        409: {"description": "An investigation case already exists for this transaction."},
    },
)
def create_case(
    request: CaseCreateRequest,
    current_user: User = Depends(require_analyst_or_admin),
    db: Session = Depends(get_db),
) -> CaseResponse:
    """Open an investigation case with atomic audit event generation."""
    # 1. Verify transaction exists
    tx = TransactionRepository.get_by_id(db, request.transaction_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID {request.transaction_id} was not found.",
        )

    # 2. Check for duplicate case
    existing_case = CaseRepository.get_by_transaction_id(db, request.transaction_id)
    if existing_case:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An investigation case already exists for transaction {request.transaction_id} (Case ID: {existing_case.id}).",
        )

    clean_description = request.description.strip() if request.description else None

    try:
        # Create case
        case = CaseRepository.create(
            db=db,
            transaction_id=request.transaction_id,
            description=clean_description,
        )

        # Record atomic audit event
        AuditLogRepository.create(
            db=db,
            actor_id=str(current_user.id),
            action="CASE_CREATED",
            entity_type="investigation_case",
            entity_id=str(case.id),
            details={
                "transaction_id": request.transaction_id,
                "status": "OPEN",
                "creator_email": current_user.email,
                "creator_role": current_user.role,
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to atomically create case: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create investigation case.",
        ) from exc

    # Refresh eager relationships
    case = CaseRepository.get_by_id(db, case.id)
    return _to_case_response(case)


@router.get(
    "",
    response_model=PaginatedCasesResponse,
    summary="List and filter investigation cases",
    description=(
        "Returns paginated investigation cases. Administrators and Auditors view all cases; "
        "Analysts view assigned cases and permitted unassigned cases."
    ),
)
def list_cases(
    page: int = Query(default=1, ge=1, description="Page index (1-based)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status_filter: str | None = Query(default=None, alias="status", description="Filter by case status"),
    assigned_user_id: int | None = Query(default=None, description="Filter by assigned analyst ID"),
    transaction_id: int | None = Query(default=None, description="Filter by transaction ID"),
    risk_level: str | None = Query(default=None, description="Filter by prediction risk level"),
    predicted_class: int | None = Query(default=None, ge=0, le=1, description="Filter by predicted class"),
    created_from: datetime | None = Query(default=None, description="Start date filter"),
    created_to: datetime | None = Query(default=None, description="End date filter"),
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
) -> PaginatedCasesResponse:
    """Retrieve filtered investigation cases based on role visibility rules."""
    if created_from and created_to and created_from > created_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date range: 'created_from' cannot be later than 'created_to'.",
        )

    is_admin_or_auditor = current_user.role.upper() in {"ADMIN", "AUDITOR"}

    records, total_count = CaseRepository.list_cases(
        db=db,
        page=page,
        page_size=page_size,
        status=status_filter,
        assigned_user_id=assigned_user_id,
        transaction_id=transaction_id,
        risk_level=risk_level,
        predicted_class=predicted_class,
        created_from=created_from,
        created_to=created_to,
        visible_user_id=current_user.id,
        is_admin_or_auditor=is_admin_or_auditor,
    )

    items = [_to_case_response(c) for c in records]
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

    return PaginatedCasesResponse(
        items=items,
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{case_id}",
    response_model=CaseDetailResponse,
    summary="Get complete investigation case details",
    description="Returns case details, associated transaction, latest prediction, and chronological notes.",
    responses={
        403: {"description": "Access denied. Case is assigned to another analyst."},
        404: {"description": "Investigation case not found."},
    },
)
def get_case_details(
    case_id: int,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
) -> CaseDetailResponse:
    """Retrieve detailed case record with role visibility enforcement."""
    case = CaseRepository.get_by_id(db, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation case with ID {case_id} was not found.",
        )

    # Visibility check for Analyst
    if current_user.role.upper() == "ANALYST":
        if case.assigned_user_id is not None and case.assigned_user_id != current_user.id:
            logger.warning(
                "Access denied for analyst %s on case %s (assigned to %s)",
                current_user.email,
                case.id,
                case.assigned_user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Case is assigned to another analyst.",
            )

    return _to_case_detail_response(case)


@router.patch(
    "/{case_id}",
    response_model=CaseResponse,
    summary="Update an investigation case",
    description="Update status, analyst assignment, or description with state machine validation.",
    responses={
        400: {"description": "Invalid assignment or update request."},
        403: {"description": "Insufficient permissions or unauthorized reassignment."},
        404: {"description": "Case or assigned user not found."},
        422: {"description": "Invalid state transition."},
    },
)
def update_case(
    case_id: int,
    request: CaseUpdateRequest,
    current_user: User = Depends(require_analyst_or_admin),
    db: Session = Depends(get_db),
) -> CaseResponse:
    """Update case status, assignment, or description atomically."""
    case = CaseRepository.get_by_id(db, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation case with ID {case_id} was not found.",
        )

    # Analyst permission checks
    is_admin = current_user.role.upper() == "ADMIN"
    if not is_admin:
        # If case is assigned to another analyst, forbid modification
        if case.assigned_user_id is not None and case.assigned_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify a case assigned to another analyst.",
            )

    try:
        # 1. Handle assignment change
        if "assigned_user_id" in request.model_fields_set:
            new_assignee_id = request.assigned_user_id
            if new_assignee_id is not None:
                # If analyst is assigning, they can only assign to themselves (claim)
                if not is_admin and new_assignee_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Analysts can only claim or assign cases to themselves.",
                    )

                assignee = UserRepository.get_by_id(db, new_assignee_id)
                if not assignee:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"User with ID {new_assignee_id} does not exist.",
                    )
                if not assignee.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot assign case to an inactive user account.",
                    )
                if assignee.role.upper() != "ANALYST":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Only users with role ANALYST can be assigned to cases. Target user has role '{assignee.role}'.",
                    )

                old_assignee_id = case.assigned_user_id
                if old_assignee_id != assignee.id:
                    case.assigned_user_id = assignee.id
                    case.assigned_user = assignee
                    case.assigned_to = assignee.email
                    AuditLogRepository.create(
                        db=db,
                        actor_id=str(current_user.id),
                        action="CASE_ASSIGNED",
                        entity_type="investigation_case",
                        entity_id=str(case.id),
                        details={
                            "old_assigned_user_id": old_assignee_id,
                            "new_assigned_user_id": assignee.id,
                            "assigned_to": assignee.email,
                        },
                    )
            else:
                # Unassigning
                if not is_admin:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only administrators are authorized to unassign cases.",
                    )
                old_assignee_id = case.assigned_user_id
                if old_assignee_id is not None:
                    case.assigned_user_id = None
                    case.assigned_user = None
                    case.assigned_to = None
                    AuditLogRepository.create(
                        db=db,
                        actor_id=str(current_user.id),
                        action="CASE_UNASSIGNED",
                        entity_type="investigation_case",
                        entity_id=str(case.id),
                        details={"old_assigned_user_id": old_assignee_id},
                    )

        # 2. Handle state transition
        if request.status is not None:
            old_status, new_status = CaseRepository.update_status(case, request.status)
            if old_status != new_status:
                AuditLogRepository.create(
                    db=db,
                    actor_id=str(current_user.id),
                    action="CASE_STATUS_CHANGED",
                    entity_type="investigation_case",
                    entity_id=str(case.id),
                    details={
                        "old_status": old_status,
                        "new_status": new_status,
                        "resolved_at": case.resolved_at.isoformat() if case.resolved_at else None,
                    },
                )

        # 3. Handle description update
        if request.description is not None:
            clean_desc = request.description.strip()
            if case.description != clean_desc:
                case.description = clean_desc
                AuditLogRepository.create(
                    db=db,
                    actor_id=str(current_user.id),
                    action="CASE_UPDATED",
                    entity_type="investigation_case",
                    entity_id=str(case.id),
                    details={"field": "description"},
                )

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except ValueError as val_err:
        db.rollback()
        logger.warning("Invalid case state transition or value: %s", val_err)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to update case: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update investigation case.",
        ) from exc

    # Refresh and return
    case = CaseRepository.get_by_id(db, case.id)
    return _to_case_response(case)


@router.post(
    "/{case_id}/notes",
    response_model=CaseNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an investigation note to a case",
    description="Adds an append-only chronological note. Cannot add notes to closed cases. Auditor denied.",
    responses={
        201: {"description": "Investigation note created."},
        400: {"description": "Empty note body."},
        403: {"description": "Insufficient permissions or unauthorized analyst."},
        404: {"description": "Case not found."},
        422: {"description": "Cannot add notes to a closed case."},
    },
)
def add_case_note(
    case_id: int,
    request: CaseNoteCreateRequest,
    current_user: User = Depends(require_analyst_or_admin),
    db: Session = Depends(get_db),
) -> CaseNoteResponse:
    """Add an append-only investigation note and record audit event."""
    case = CaseRepository.get_by_id(db, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation case with ID {case_id} was not found.",
        )

    # Closed cases are terminal; no new notes allowed
    if case.status == "CLOSED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot add notes to a CLOSED case. Investigation is closed.",
        )

    # Analyst visibility check
    if current_user.role.upper() == "ANALYST":
        if case.assigned_user_id is not None and case.assigned_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot add notes to a case assigned to another analyst.",
            )

    clean_body = request.body.strip()
    if not clean_body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Note body cannot be empty or contain only whitespace.",
        )

    try:
        note = CaseNoteRepository.create(
            db=db,
            case_id=case.id,
            author_id=current_user.id,
            author_name=current_user.name,
            author_email=current_user.email,
            author_role=current_user.role,
            body=clean_body,
        )

        AuditLogRepository.create(
            db=db,
            actor_id=str(current_user.id),
            action="CASE_NOTE_ADDED",
            entity_type="investigation_case",
            entity_id=str(case.id),
            details={"note_id": note.id, "author": current_user.email},
        )
        db.commit()
        db.refresh(note)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to add case note: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record case note.",
        ) from exc

    return CaseNoteResponse(
        id=note.id,
        case_id=note.case_id,
        author_id=note.author_id,
        author_name=note.author_name,
        author_email=note.author_email,
        author_role=note.author_role,
        body=note.body,
        created_at=note.created_at,
    )


@router.get(
    "/{case_id}/notes",
    response_model=PaginatedCaseNotesResponse,
    summary="List investigation notes for a case",
    description="Returns notes in chronological order (oldest first). Safe author profiles.",
    responses={
        403: {"description": "Access denied for restricted cases."},
        404: {"description": "Case not found."},
    },
)
def list_case_notes(
    case_id: int,
    page: int = Query(default=1, ge=1, description="Page index (1-based)"),
    page_size: int = Query(default=100, ge=1, le=200, description="Items per page"),
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
) -> PaginatedCaseNotesResponse:
    """Retrieve chronological notes for an investigation case."""
    case = CaseRepository.get_by_id(db, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation case with ID {case_id} was not found.",
        )

    # Analyst visibility check
    if current_user.role.upper() == "ANALYST":
        if case.assigned_user_id is not None and case.assigned_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Case is assigned to another analyst.",
            )

    records, total_count = CaseNoteRepository.list_by_case(
        db=db,
        case_id=case_id,
        page=page,
        page_size=page_size,
    )

    items = [
        CaseNoteResponse(
            id=note.id,
            case_id=note.case_id,
            author_id=note.author_id,
            author_name=note.author_name,
            author_email=note.author_email,
            author_role=note.author_role,
            body=note.body,
            created_at=note.created_at,
        )
        for note in records
    ]
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

    return PaginatedCaseNotesResponse(
        items=items,
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
