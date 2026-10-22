"""Health check and service readiness endpoint."""

from fastapi import APIRouter, Response, status

from app.config import get_settings
from app.schemas.prediction import HealthResponse
from app.services.predictor import predictor_service

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check service health and model readiness",
    description="Returns service availability and whether the machine learning model pipeline is loaded and ready for inference.",
)
def get_health(response: Response) -> HealthResponse:
    """Evaluate service health and ML pipeline readiness."""
    settings = get_settings()
    is_ready = predictor_service.is_ready()

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(
            status="unavailable",
            model_loaded=False,
            model_version=None,
            model_type=None,
            environment=settings.ENVIRONMENT,
        )

    return HealthResponse(
        status="healthy",
        model_loaded=True,
        model_version=predictor_service.model_version,
        model_type=predictor_service.model_type,
        environment=settings.ENVIRONMENT,
    )
