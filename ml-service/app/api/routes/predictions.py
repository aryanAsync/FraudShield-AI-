"""Internal prediction and model metadata endpoints for FraudShield AI."""

import logging

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.prediction import (
    BatchPredictionResponse,
    ModelInfoResponse,
    PredictionResponse,
    PredictionWithExplanationResponse,
)
from app.schemas.transaction import BatchTransactionInput, TransactionInput
from app.services.predictor import predictor_service

logger = logging.getLogger("prediction_routes")
router = APIRouter(prefix="/internal", tags=["Predictions & Model Operations"])


@router.get(
    "/model-info",
    response_model=ModelInfoResponse,
    summary="Retrieve active model metadata and metrics",
    description="Returns public model specifications, features, trained thresholds, and evaluation metrics without exposing filesystem paths or credentials.",
)
def get_model_information() -> ModelInfoResponse:
    """Retrieve metadata and evaluation metrics for currently deployed model."""
    if not predictor_service.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is not loaded. Prediction service unavailable.",
        )
    return predictor_service.get_model_info()


@router.post(
    "/predict",
    response_model=PredictionWithExplanationResponse | PredictionResponse,
    summary="Score fraud risk for a single transaction",
    description=(
        "Evaluates a single credit card transaction feature vector against the fitted ML pipeline. "
        "Strictly validates feature schema, rejects non-finite values and unrecognized fields, "
        "and computes fraud probability, calibrated risk score, and risk category."
    ),
    responses={
        200: {
            "description": "Inference successful with risk score and prediction.",
        },
        400: {"description": "Invalid input values or unprocessable transaction data."},
        422: {
            "description": "Schema validation failure (missing features or unexpected fields like Class)."
        },
        503: {"description": "Model pipeline is not loaded into memory."},
    },
)
def predict_transaction(
    transaction: TransactionInput,
    explain: bool = Query(
        default=False,
        description="Whether to include SHAP feature attribution explanations",
    ),
    threshold: float | None = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional threshold override for this inference request",
    ),
) -> PredictionResponse | PredictionWithExplanationResponse:
    """Execute risk scoring for one transaction."""
    if not predictor_service.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is not loaded. Cannot process inference.",
        )

    try:
        result = predictor_service.predict_single(
            transaction=transaction,
            threshold_override=threshold,
            include_explanation=explain,
        )
        return result
    except ValueError as val_err:
        logger.error("Validation error during inference: %s", val_err)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        logger.exception("Unexpected error during inference: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal inference failure.",
        ) from exc


@router.post(
    "/predict/batch",
    response_model=BatchPredictionResponse,
    summary="Batch score multiple transactions",
    description="Evaluates a batch of transactions with memory safety constraints and strict ordering preservation.",
    responses={
        200: {"description": "Batch inference completed successfully."},
        400: {
            "description": "Batch payload exceeds maximum allowed size or contains invalid rows."
        },
        503: {"description": "Model pipeline is not loaded into memory."},
    },
)
def predict_batch_transactions(
    batch_input: BatchTransactionInput,
    threshold: float | None = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional threshold override for all transactions in this batch",
    ),
) -> BatchPredictionResponse:
    """Execute batch inference across a list of transactions."""
    if not predictor_service.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is not loaded. Cannot process inference.",
        )

    try:
        return predictor_service.predict_batch(batch_input, threshold_override=threshold)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        logger.exception("Unexpected error during batch inference: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal batch inference failure.",
        ) from exc
