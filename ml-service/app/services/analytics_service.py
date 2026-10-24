"""Business logic and analytics coordination service for FraudShield AI."""

import logging
import math
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsFilterSummary,
    AnalyticsOverviewResponse,
    AnalyticsTrendsResponse,
    CaseStatusDistributionItem,
    CaseStatusDistributionResponse,
    CaseStatusSummary,
    ClassificationDistributionSummary,
    FeatureImportanceItem,
    FeatureImportanceResponse,
    OverviewCasesSummary,
    OverviewPredictionsSummary,
    OverviewRiskSummary,
    OverviewTransactionsSummary,
    RiskDistributionItem,
    RiskDistributionResponse,
    TrendBucketItem,
)

logger = logging.getLogger("analytics_service")


class AnalyticsService:
    """Coordinates metric extraction, validation, and serialization for fraud analytics."""

    @classmethod
    def validate_date_range(
        cls,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> tuple[datetime | None, datetime | None]:
        """Normalize naive/aware timestamps to UTC and validate start_date <= end_date.

        Ensures timezone consistency by converting offset-aware datetimes to UTC
        and assuming UTC for naive inputs, preventing Python comparison TypeErrors.
        """
        norm_start = start_date
        norm_end = end_date

        if norm_start is not None:
            if norm_start.tzinfo is None:
                norm_start = norm_start.replace(tzinfo=UTC)
            else:
                norm_start = norm_start.astimezone(UTC)

        if norm_end is not None:
            if norm_end.tzinfo is None:
                norm_end = norm_end.replace(tzinfo=UTC)
            else:
                norm_end = norm_end.astimezone(UTC)

        if norm_start is not None and norm_end is not None and norm_start > norm_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date range: 'start_date' cannot be later than 'end_date'.",
            )
        return norm_start, norm_end

    @classmethod
    def get_overview(
        cls,
        db: Session,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> AnalyticsOverviewResponse:
        """Retrieve overview KPIs for high-level dashboard cards."""
        start_date, end_date = cls.validate_date_range(start_date, end_date)
        raw = AnalyticsRepository.get_overview_metrics(db, start_date=start_date, end_date=end_date)

        return AnalyticsOverviewResponse(
            filters=AnalyticsFilterSummary(**raw["filters"]),
            transactions=OverviewTransactionsSummary(**raw["transactions"]),
            predictions=OverviewPredictionsSummary(**raw["predictions"]),
            risk=OverviewRiskSummary(**raw["risk"]),
            cases=OverviewCasesSummary(**raw["cases"]),
        )

    @classmethod
    def get_risk_distribution(
        cls,
        db: Session,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> RiskDistributionResponse:
        """Retrieve risk tier counts and classification decisions based on latest predictions."""
        start_date, end_date = cls.validate_date_range(start_date, end_date)
        raw = AnalyticsRepository.get_risk_distribution(db, start_date=start_date, end_date=end_date)

        return RiskDistributionResponse(
            total_transactions=raw["total_transactions"],
            items=[RiskDistributionItem(**it) for it in raw["items"]],
            classification=ClassificationDistributionSummary(**raw["classification"]),
        )

    @classmethod
    def get_trends(
        cls,
        db: Session,
        interval: str = "day",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> AnalyticsTrendsResponse:
        """Retrieve time-series inference event trends."""
        normalized_interval = interval.lower().strip()
        if normalized_interval not in {"hour", "day"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid interval: must be either 'hour' or 'day'.",
            )

        start_date, end_date = cls.validate_date_range(start_date, end_date)

        # Enforce maximum query window to protect against unbounded scans
        if start_date is not None and end_date is not None:
            diff = end_date - start_date
            if normalized_interval == "hour" and diff > timedelta(days=30):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Date range too large for hourly interval. Maximum allowed range is 30 days.",
                )
            if normalized_interval == "day" and diff > timedelta(days=365):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Date range too large for daily interval. Maximum allowed range is 365 days.",
                )

        raw_buckets = AnalyticsRepository.get_trends(
            db=db,
            interval=normalized_interval,
            start_date=start_date,
            end_date=end_date,
        )

        bucket_items = [TrendBucketItem(**b) for b in raw_buckets]
        return AnalyticsTrendsResponse(
            interval=normalized_interval,
            metrics={
                "timestamp_field": "predicted_at",
                "description": "Inference evaluation events grouped by predicted_at timestamp.",
            },
            items=bucket_items,
        )

    @classmethod
    def get_case_status_distribution(
        cls,
        db: Session,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> CaseStatusDistributionResponse:
        """Retrieve investigation case status distribution and resolution metrics."""
        start_date, end_date = cls.validate_date_range(start_date, end_date)
        raw = AnalyticsRepository.get_case_status_distribution(db, start_date=start_date, end_date=end_date)

        return CaseStatusDistributionResponse(
            total_cases=raw["total_cases"],
            items=[CaseStatusDistributionItem(**it) for it in raw["items"]],
            summary=CaseStatusSummary(**raw["summary"]),
        )

    @classmethod
    def get_feature_importance(
        cls,
        db: Session,
        risk_level: str | None = "HIGH",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 10,
    ) -> FeatureImportanceResponse:
        """Aggregate absolute SHAP feature attributions across high-risk transaction predictions."""
        start_date, end_date = cls.validate_date_range(start_date, end_date)

        normalized_risk: str | None = None
        if risk_level is not None:
            normalized_risk = risk_level.upper().strip()
            if normalized_risk not in {"LOW", "MEDIUM", "HIGH"}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid risk_level '{risk_level}'. Must be 'LOW', 'MEDIUM', or 'HIGH'.",
                )

        raw_explanations = AnalyticsRepository.get_feature_importance_explanations(
            db=db,
            risk_level=normalized_risk,
            start_date=start_date,
            end_date=end_date,
            sample_limit=100,
        )

        feature_totals: dict[str, float] = {}
        feature_counts: dict[str, int] = {}
        valid_sample_count = 0

        for expl in raw_explanations:
            if isinstance(expl, list) and len(expl) > 0:
                valid_sample_count += 1
                for item in expl:
                    if isinstance(item, dict) and "feature" in item and "attribution" in item:
                        feat_name = str(item["feature"])
                        try:
                            attr_val = float(item["attribution"])
                            if math.isfinite(attr_val):
                                feature_totals[feat_name] = feature_totals.get(feat_name, 0.0) + abs(attr_val)
                                feature_counts[feat_name] = feature_counts.get(feat_name, 0) + 1
                        except (ValueError, TypeError):
                            continue

        ranked_items: list[FeatureImportanceItem] = []
        if feature_totals:
            # Sort by mean absolute attribution descending
            sorted_features = sorted(
                feature_totals.keys(),
                key=lambda f: (feature_totals[f] / feature_counts[f]),
                reverse=True,
            )

            for rank, feat in enumerate(sorted_features[:limit], start=1):
                cnt = feature_counts[feat]
                mean_abs = round(feature_totals[feat] / cnt, 4) if cnt > 0 else 0.0
                ranked_items.append(
                    FeatureImportanceItem(
                        rank=rank,
                        feature=feat,
                        mean_absolute_attribution=mean_abs,
                        sample_count=cnt,
                    )
                )

        return FeatureImportanceResponse(
            sample_size=valid_sample_count,
            target_risk_level=normalized_risk,
            features=ranked_items,
        )
