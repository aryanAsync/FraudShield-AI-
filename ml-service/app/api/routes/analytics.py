"""API endpoints for dashboard analytics, risk distributions, trends, and feature importance."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_any_authenticated
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    AnalyticsTrendsResponse,
    CaseStatusDistributionResponse,
    FeatureImportanceResponse,
    RiskDistributionResponse,
)
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger("analytics_routes")

router = APIRouter(prefix="/api/v1/analytics", tags=["Dashboard Analytics"])


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Get dashboard overview KPIs",
    description=(
        "Returns top-level metric cards including total transactions, evaluation counts, "
        "model-predicted fraud rate, average risk score, and investigation case pipeline counts. "
        "Uses the latest prediction per transaction to prevent double counting. "
        "Accessible to ADMIN, ANALYST, and AUDITOR roles."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid date range parameters."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid authentication token."},
    },
)
def get_analytics_overview(
    start_date: datetime | None = Query(default=None, description="Earliest timestamp filter (UTC)"),
    end_date: datetime | None = Query(default=None, description="Latest timestamp filter (UTC)"),
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
) -> AnalyticsOverviewResponse:
    """Retrieve high-level dashboard metrics for transactions, predictions, and cases."""
    return AnalyticsService.get_overview(
        db=db,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/risk-distribution",
    response_model=RiskDistributionResponse,
    summary="Get current risk tier and classification distribution",
    description=(
        "Returns the distribution of transactions across risk categories (LOW, MEDIUM, HIGH) "
        "and binary classification decisions (predicted fraud vs legitimate). "
        "Strictly evaluated on the latest prediction for each transaction. "
        "Accessible to ADMIN, ANALYST, and AUDITOR roles."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid date range parameters."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid authentication token."},
    },
)
def get_risk_distribution(
    start_date: datetime | None = Query(default=None, description="Earliest timestamp filter (UTC)"),
    end_date: datetime | None = Query(default=None, description="Latest timestamp filter (UTC)"),
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
) -> RiskDistributionResponse:
    """Retrieve risk level breakdown and classification decisions."""
    return AnalyticsService.get_risk_distribution(
        db=db,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/trends",
    response_model=AnalyticsTrendsResponse,
    summary="Get transaction and prediction time-series trends",
    description=(
        "Returns time-series metrics aggregated by hourly or daily buckets. "
        "Includes prediction evaluation volume, distinct transaction volume, "
        "flagged fraud counts, and average risk score. "
        "Accessible to ADMIN, ANALYST, and AUDITOR roles."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid interval or date range exceeding limit."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid authentication token."},
    },
)
def get_analytics_trends(
    interval: str = Query(default="day", description="Time bucket interval: 'hour' or 'day'"),
    start_date: datetime | None = Query(default=None, description="Earliest timestamp filter (UTC)"),
    end_date: datetime | None = Query(default=None, description="Latest timestamp filter (UTC)"),
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
) -> AnalyticsTrendsResponse:
    """Retrieve time-series inference trends."""
    return AnalyticsService.get_trends(
        db=db,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/case-status-distribution",
    response_model=CaseStatusDistributionResponse,
    summary="Get investigation case status distribution",
    description=(
        "Returns case counts and proportions by status (OPEN, IN_REVIEW, CONFIRMED_FRAUD, "
        "LEGITIMATE, CLOSED), along with assignment stats and average resolution time in seconds. "
        "Accessible to ADMIN, ANALYST, and AUDITOR roles."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid date range parameters."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid authentication token."},
    },
)
def get_case_status_distribution(
    start_date: datetime | None = Query(default=None, description="Earliest timestamp filter (UTC)"),
    end_date: datetime | None = Query(default=None, description="Latest timestamp filter (UTC)"),
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
) -> CaseStatusDistributionResponse:
    """Retrieve investigation case status distribution and workload metrics."""
    return AnalyticsService.get_case_status_distribution(
        db=db,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/feature-importance",
    response_model=FeatureImportanceResponse,
    summary="Get aggregated model explanation feature importance",
    description=(
        "Aggregates SHAP feature attribution contributions across high-risk transaction predictions. "
        "Returns top features ranked by mean absolute contribution to explain primary risk drivers. "
        "Accessible to ADMIN, ANALYST, and AUDITOR roles."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid risk level or date range parameters."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid authentication token."},
    },
)
def get_feature_importance(
    risk_level: str | None = Query(default="HIGH", description="Filter by risk tier: 'LOW', 'MEDIUM', or 'HIGH'"),
    limit: int = Query(default=10, ge=1, le=30, description="Top N features to return"),
    start_date: datetime | None = Query(default=None, description="Earliest timestamp filter (UTC)"),
    end_date: datetime | None = Query(default=None, description="Latest timestamp filter (UTC)"),
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
) -> FeatureImportanceResponse:
    """Retrieve aggregated SHAP feature importance for risk analysis."""
    return AnalyticsService.get_feature_importance(
        db=db,
        risk_level=risk_level,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
