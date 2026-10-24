"""Transaction persistence and fraud scoring API routes for FraudShield AI."""

import logging
import math
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_analyst_or_admin, require_any_authenticated
from app.db.models.user import User
from app.db.repositories.prediction_repository import PredictionRepository
from app.db.repositories.transaction_repository import TransactionRepository
from app.db.session import get_db
from app.schemas.persistence import (
    PaginatedTransactionsResponse,
    PredictionHistoryResponse,
    PredictionRecordResponse,
    ScoreTransactionRequest,
    ScoreTransactionResponse,
    TransactionDetailResponse,
    TransactionSummaryResponse,
)
from app.schemas.prediction import RiskLevel
from app.schemas.transaction import TransactionInput
from app.services.predictor import predictor_service

logger = logging.getLogger("transaction_routes")

router = APIRouter(prefix="/api/v1/transactions", tags=["Transactions & Persistence"])


def _to_prediction_record(pred) -> PredictionRecordResponse:
    """Format SQLAlchemy Prediction model to Pydantic schema."""
    return PredictionRecordResponse(
        id=pred.id,
        transaction_id=pred.transaction_id,
        fraud_probability=pred.fraud_probability,
        risk_score=pred.risk_score,
        predicted_class=pred.predicted_class,
        risk_level=RiskLevel(pred.risk_level),
        decision_threshold=pred.decision_threshold,
        model_version=pred.model_version,
        explanation=pred.explanation,
        predicted_at=pred.predicted_at,
    )


@router.post(
    "/score",
    response_model=ScoreTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Score and persist a financial transaction",
    description=(
        "Executes machine learning fraud scoring and atomically saves both the transaction vector "
        "and its prediction outcome in PostgreSQL within a single database transaction."
    ),
    responses={
        201: {"description": "Transaction and prediction persisted successfully."},
        400: {"description": "Invalid input features or unprocessable data."},
        409: {"description": "A transaction with the provided external_reference already exists."},
        422: {"description": "Schema validation failure."},
        503: {"description": "Predictor model pipeline is not available."},
    },
)
def score_and_persist_transaction(
    request: ScoreTransactionRequest,
    current_user: User = Depends(require_analyst_or_admin),
    db: Session = Depends(get_db),
) -> ScoreTransactionResponse:
    """Evaluate fraud risk on a transaction and persist both records atomically."""
    if not predictor_service.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Machine learning model pipeline is not ready for inference.",
        )

    # Check for external_reference uniqueness before heavy computation
    if request.external_reference:
        existing = TransactionRepository.get_by_external_reference(db, request.external_reference)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Transaction with external reference '{request.external_reference}' already exists.",
            )

    # Reconstruct pure feature vector for model pipeline
    feature_payload = {f"V{i}": getattr(request, f"V{i}") for i in range(1, 29)}
    tx_input_dict = {
        "Time": request.Time,
        "Amount": request.Amount,
        **feature_payload,
    }
    tx_input = TransactionInput(**tx_input_dict)

    # 1. Run inference
    try:
        prediction_result = predictor_service.predict_single(
            transaction=tx_input,
            threshold_override=request.threshold,
            include_explanation=request.explain,
        )
    except ValueError as val_err:
        logger.warning("Feature validation error during scoring: %s", val_err)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        logger.exception("Unexpected inference error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Inference execution failed.",
        ) from exc

    # Prepare serialized explanation if available
    raw_explanation = None
    if getattr(prediction_result, "top_risk_factors", None):
        raw_explanation = [factor.model_dump() for factor in prediction_result.top_risk_factors]

    # 2. Persist transaction and prediction atomically
    try:
        # Create transaction record
        tx = TransactionRepository.create(
            db=db,
            transaction_time=request.Time,
            amount=request.Amount,
            features=feature_payload,
            external_reference=request.external_reference,
            submitted_by=request.submitted_by or current_user.email,
        )

        # Create prediction record linked to transaction
        pred = PredictionRepository.create(
            db=db,
            transaction_id=tx.id,
            fraud_probability=prediction_result.fraud_probability,
            risk_score=prediction_result.risk_score,
            predicted_class=prediction_result.predicted_class,
            risk_level=prediction_result.risk_level.value,
            decision_threshold=prediction_result.threshold,
            model_version=prediction_result.model_version,
            explanation=raw_explanation,
        )

        # Single atomic commit
        db.commit()
        db.refresh(tx)
        db.refresh(pred)
    except IntegrityError as int_err:
        db.rollback()
        logger.error("Database integrity constraint violation during scoring: %s", int_err)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Data integrity constraint violated while persisting transaction or prediction.",
        ) from int_err
    except Exception as exc:
        db.rollback()
        logger.exception("Database persistence failure during scoring: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist transaction and prediction records.",
        ) from exc

    return ScoreTransactionResponse(
        transaction_id=tx.id,
        external_reference=tx.external_reference,
        transaction_time=tx.transaction_time,
        amount=tx.amount,
        submitted_by=tx.submitted_by,
        created_at=tx.created_at,
        prediction=_to_prediction_record(pred),
    )


@router.get(
    "",
    response_model=PaginatedTransactionsResponse,
    summary="List transactions with pagination and risk filters",
    description="Returns a paginated list of stored transactions, optionally filtered by risk level or predicted class.",
)
def list_transactions(
    page: int = Query(default=1, ge=1, description="Page index (1-based)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    risk_level: RiskLevel | None = Query(default=None, description="Filter by risk tier"),
    predicted_class: int | None = Query(
        default=None, ge=0, le=1, description="Filter by binary classification (0 or 1)"
    ),
    sort_by: Literal["created_at", "amount", "transaction_time", "id"] = Query(
        default="created_at", description="Field to sort on"
    ),
    sort_order: Literal["asc", "desc"] = Query(default="desc", description="Sorting direction"),
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
) -> PaginatedTransactionsResponse:
    """Retrieve paginated transactions with optional risk filters."""
    records, total_count = TransactionRepository.list_transactions(
        db=db,
        page=page,
        page_size=page_size,
        risk_level=risk_level.value if risk_level else None,
        predicted_class=predicted_class,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    items: list[TransactionSummaryResponse] = []
    for tx in records:
        latest_pred = tx.predictions[0] if tx.predictions else None
        items.append(
            TransactionSummaryResponse(
                id=tx.id,
                external_reference=tx.external_reference,
                transaction_time=tx.transaction_time,
                amount=tx.amount,
                submitted_by=tx.submitted_by,
                created_at=tx.created_at,
                latest_prediction=_to_prediction_record(latest_pred) if latest_pred else None,
            )
        )

    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

    return PaginatedTransactionsResponse(
        items=items,
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionDetailResponse,
    summary="Retrieve detailed transaction record",
    description="Returns full transaction details, anonymized PCA features, and latest prediction summary.",
    responses={
        404: {"description": "Transaction not found."},
    },
)
def get_transaction_details(
    transaction_id: int,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
) -> TransactionDetailResponse:
    """Retrieve transaction details by ID."""
    tx = TransactionRepository.get_by_id(db, transaction_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID {transaction_id} was not found.",
        )

    latest_pred = tx.predictions[0] if tx.predictions else None
    return TransactionDetailResponse(
        id=tx.id,
        external_reference=tx.external_reference,
        transaction_time=tx.transaction_time,
        amount=tx.amount,
        features=tx.features,
        submitted_by=tx.submitted_by,
        created_at=tx.created_at,
        latest_prediction=_to_prediction_record(latest_pred) if latest_pred else None,
        predictions_count=len(tx.predictions),
    )


@router.get(
    "/{transaction_id}/predictions",
    response_model=PredictionHistoryResponse,
    summary="Retrieve prediction evaluation history for a transaction",
    description="Returns all historical prediction snapshots recorded for this transaction, ordered newest first.",
    responses={
        404: {"description": "Transaction not found."},
    },
)
def get_transaction_predictions(
    transaction_id: int,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
) -> PredictionHistoryResponse:
    """Retrieve full prediction history for a given transaction."""
    tx = TransactionRepository.get_by_id(db, transaction_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID {transaction_id} was not found.",
        )

    predictions = PredictionRepository.get_by_transaction_id(db, transaction_id)
    return PredictionHistoryResponse(
        transaction_id=transaction_id,
        total_evaluations=len(predictions),
        predictions=[_to_prediction_record(p) for p in predictions],
    )
