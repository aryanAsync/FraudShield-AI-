"""FastAPI Application Entrypoint for FraudShield AI Machine Learning Service."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health, predictions
from app.config import get_settings
from app.services.predictor import predictor_service

settings = get_settings()

# Configure root logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fraudshield_api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler: load model artifact once on startup, clean up on shutdown."""
    logger.info("Starting FraudShield AI ML Service in %s mode...", settings.ENVIRONMENT)
    try:
        predictor_service.load_model()
        logger.info("Model pipeline successfully loaded during application startup.")
    except Exception as exc:
        logger.warning(
            "Model artifact could not be loaded at startup: %s. "
            "Endpoints requiring the model will return 503 until artifact is provided.",
            exc,
        )
    yield
    logger.info("Shutting down FraudShield AI ML Service.")


app = FastAPI(
    title="FraudShield AI — Machine Learning Service",
    description=(
        "Production-ready inference service for credit card fraud detection and risk monitoring. "
        "Provides probabilistic risk scoring, calibrated risk categorization, batch inference, "
        "and SHAP feature attribution explanations."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware for local integration and Spring Boot backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Provide formatted, actionable error payloads for request validation failures."""
    logger.warning("Request schema validation failed on %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": "Input transaction payload does not match expected schema or contains forbidden fields.",
            "details": jsonable_encoder(exc.errors()),
        },
    )


# Register routes
app.include_router(health.router)
app.include_router(predictions.router)


@app.get("/", include_in_schema=False)
def root_redirect() -> dict:
    """Root redirect pointer to Swagger documentation."""
    return {
        "service": "FraudShield AI ML Service",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_check": "/health",
    }
