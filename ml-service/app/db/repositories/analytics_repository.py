"""Repository encapsulating SQL-level aggregation and analytics queries for FraudShield AI."""

from datetime import datetime
from typing import Any

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.db.models.investigation_case import InvestigationCase
from app.db.models.prediction import Prediction
from app.db.models.transaction import Transaction


class AnalyticsRepository:
    """Provides high-performance, SQL-level aggregation queries for analytics dashboards."""

    @staticmethod
    def get_latest_predictions_subquery(
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Any:
        """Build a window-function subquery ranking predictions per transaction (newest first).

        Tie-breaking rule:
            1. predicted_at DESC
            2. id DESC
        Filtering by rn == 1 guarantees exactly one latest prediction record per transaction.
        """
        subq = select(
            Prediction.id,
            Prediction.transaction_id,
            Prediction.fraud_probability,
            Prediction.risk_score,
            Prediction.predicted_class,
            Prediction.risk_level,
            Prediction.decision_threshold,
            Prediction.model_version,
            Prediction.explanation,
            Prediction.predicted_at,
            func.row_number()
            .over(
                partition_by=Prediction.transaction_id,
                order_by=(Prediction.predicted_at.desc(), Prediction.id.desc()),
            )
            .label("rn"),
        )
        if start_date is not None:
            subq = subq.where(Prediction.predicted_at >= start_date)
        if end_date is not None:
            subq = subq.where(Prediction.predicted_at <= end_date)

        return subq.subquery("latest_preds")

    @staticmethod
    def get_overview_metrics(
        db: Session,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Compute high-level overview KPIs across transactions, predictions, and cases."""
        # 1. Total distinct transactions matching creation window
        tx_stmt = select(func.count(Transaction.id))
        if start_date is not None:
            tx_stmt = tx_stmt.where(Transaction.created_at >= start_date)
        if end_date is not None:
            tx_stmt = tx_stmt.where(Transaction.created_at <= end_date)
        total_transactions = db.scalar(tx_stmt) or 0

        # 2. Total prediction evaluation runs matching predicted_at window
        pred_stmt = select(func.count(Prediction.id))
        if start_date is not None:
            pred_stmt = pred_stmt.where(Prediction.predicted_at >= start_date)
        if end_date is not None:
            pred_stmt = pred_stmt.where(Prediction.predicted_at <= end_date)
        total_predictions = db.scalar(pred_stmt) or 0

        # 3. Latest prediction metrics (1 record per transaction)
        lp = AnalyticsRepository.get_latest_predictions_subquery(start_date, end_date)
        lp_stmt = (
            select(
                func.count(lp.c.transaction_id).label("evaluated_tx_count"),
                func.count().filter(lp.c.predicted_class == 1).label("fraud_count"),
                func.count().filter(lp.c.predicted_class == 0).label("legit_count"),
                func.avg(lp.c.risk_score).label("avg_risk_score"),
                func.avg(lp.c.fraud_probability).label("avg_fraud_prob"),
                func.count().filter(lp.c.risk_level == "HIGH").label("high_risk_count"),
                func.count().filter(lp.c.risk_level == "MEDIUM").label("medium_risk_count"),
                func.count().filter(lp.c.risk_level == "LOW").label("low_risk_count"),
            )
            .where(lp.c.rn == 1)
        )
        lp_row = db.execute(lp_stmt).first()

        evaluated_tx_count = lp_row.evaluated_tx_count if lp_row else 0
        fraud_count = lp_row.fraud_count if lp_row else 0
        legit_count = lp_row.legit_count if lp_row else 0
        avg_risk_score = float(lp_row.avg_risk_score) if (lp_row and lp_row.avg_risk_score is not None) else 0.0
        avg_fraud_prob = float(lp_row.avg_fraud_prob) if (lp_row and lp_row.avg_fraud_prob is not None) else 0.0
        high_risk_count = lp_row.high_risk_count if lp_row else 0
        medium_risk_count = lp_row.medium_risk_count if lp_row else 0
        low_risk_count = lp_row.low_risk_count if lp_row else 0

        predicted_fraud_percentage = (
            round((fraud_count / evaluated_tx_count) * 100.0, 2)
            if evaluated_tx_count > 0
            else 0.0
        )

        # 4. Investigation case metrics
        case_stmt = select(
            func.count(InvestigationCase.id).label("total_cases"),
            func.count().filter(InvestigationCase.status == "OPEN").label("open_count"),
            func.count().filter(InvestigationCase.status == "IN_REVIEW").label("in_review_count"),
            func.count().filter(InvestigationCase.status == "CONFIRMED_FRAUD").label("confirmed_fraud_count"),
            func.count().filter(InvestigationCase.status == "LEGITIMATE").label("legitimate_count"),
            func.count().filter(InvestigationCase.status == "CLOSED").label("closed_count"),
        )
        if start_date is not None:
            case_stmt = case_stmt.where(InvestigationCase.created_at >= start_date)
        if end_date is not None:
            case_stmt = case_stmt.where(InvestigationCase.created_at <= end_date)
        case_row = db.execute(case_stmt).first()

        total_cases = case_row.total_cases if case_row else 0
        open_cases = case_row.open_count if case_row else 0
        in_review_cases = case_row.in_review_count if case_row else 0
        confirmed_fraud_cases = case_row.confirmed_fraud_count if case_row else 0
        legitimate_cases = case_row.legitimate_count if case_row else 0
        closed_cases = case_row.closed_count if case_row else 0

        unresolved_cases = open_cases + in_review_cases
        resolved_cases = confirmed_fraud_cases + legitimate_cases + closed_cases

        return {
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
            },
            "transactions": {
                "total_transactions": total_transactions,
                "transactions_with_predictions": evaluated_tx_count,
                "predicted_fraud_count": fraud_count,
                "predicted_legitimate_count": legit_count,
                "predicted_fraud_percentage": predicted_fraud_percentage,
            },
            "predictions": {
                "total_predictions": total_predictions,
            },
            "risk": {
                "average_risk_score": round(avg_risk_score, 2),
                "average_fraud_probability": round(avg_fraud_prob, 4),
                "high_risk_transactions": high_risk_count,
                "medium_risk_transactions": medium_risk_count,
                "low_risk_transactions": low_risk_count,
            },
            "cases": {
                "total_cases": total_cases,
                "open": open_cases,
                "in_review": in_review_cases,
                "confirmed_fraud": confirmed_fraud_cases,
                "legitimate": legitimate_cases,
                "closed": closed_cases,
                "unresolved": unresolved_cases,
                "resolved": resolved_cases,
            },
        }

    @staticmethod
    def get_risk_distribution(
        db: Session,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Aggregate current risk tiers and classification decisions for latest predictions."""
        lp = AnalyticsRepository.get_latest_predictions_subquery(start_date, end_date)

        # 1. Tier counts
        tier_stmt = (
            select(
                lp.c.risk_level,
                func.count(lp.c.transaction_id).label("tier_count"),
            )
            .where(lp.c.rn == 1)
            .group_by(lp.c.risk_level)
        )
        tier_rows = db.execute(tier_stmt).all()
        tier_map = {row.risk_level: row.tier_count for row in tier_rows}

        # 2. Binary classification counts
        class_stmt = (
            select(
                func.count(lp.c.transaction_id).label("total"),
                func.count().filter(lp.c.predicted_class == 1).label("fraud_count"),
                func.count().filter(lp.c.predicted_class == 0).label("legit_count"),
            )
            .where(lp.c.rn == 1)
        )
        class_row = db.execute(class_stmt).first()
        total_eval = class_row.total if class_row else 0
        fraud_count = class_row.fraud_count if class_row else 0
        legit_count = class_row.legit_count if class_row else 0

        # Construct deterministic tier list: LOW, MEDIUM, HIGH
        items = []
        for tier in ["LOW", "MEDIUM", "HIGH"]:
            c = tier_map.get(tier, 0)
            pct = round((c / total_eval) * 100.0, 2) if total_eval > 0 else 0.0
            items.append({"risk_level": tier, "count": c, "percentage": pct})

        fraud_pct = round((fraud_count / total_eval) * 100.0, 2) if total_eval > 0 else 0.0
        legit_pct = round((legit_count / total_eval) * 100.0, 2) if total_eval > 0 else 0.0

        return {
            "total_transactions": total_eval,
            "items": items,
            "classification": {
                "predicted_fraud_count": fraud_count,
                "predicted_fraud_percentage": fraud_pct,
                "predicted_legitimate_count": legit_count,
                "predicted_legitimate_percentage": legit_pct,
            },
        }

    @staticmethod
    def get_trends(
        db: Session,
        interval: str = "day",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Compute time-series prediction events aggregated into hourly or daily buckets."""
        is_pg = db.bind is not None and db.bind.dialect.name == "postgresql"
        if is_pg:
            bucket_expr = func.date_trunc(interval, Prediction.predicted_at)
        else:
            fmt = "%Y-%m-%d %H:00:00" if interval == "hour" else "%Y-%m-%d 00:00:00"
            bucket_expr = func.strftime(fmt, Prediction.predicted_at)

        stmt = (
            select(
                bucket_expr.label("bucket_time"),
                func.count(Prediction.id).label("prediction_count"),
                func.count(func.distinct(Prediction.transaction_id)).label("distinct_transactions"),
                func.count().filter(Prediction.predicted_class == 1).label("predicted_fraud_count"),
                func.count().filter(Prediction.predicted_class == 0).label("predicted_legitimate_count"),
                func.count().filter(Prediction.risk_level == "HIGH").label("high_risk_count"),
                func.avg(Prediction.risk_score).label("avg_risk_score"),
            )
            .group_by(bucket_expr)
            .order_by(bucket_expr.asc())
        )
        if start_date is not None:
            stmt = stmt.where(Prediction.predicted_at >= start_date)
        if end_date is not None:
            stmt = stmt.where(Prediction.predicted_at <= end_date)

        rows = db.execute(stmt).all()
        buckets: list[dict[str, Any]] = []
        for r in rows:
            raw_ts = r.bucket_time
            # Format cleanly to datetime if string (SQLite)
            if isinstance(raw_ts, str):
                try:
                    ts = datetime.fromisoformat(raw_ts)
                except ValueError:
                    ts = datetime.strptime(raw_ts, "%Y-%m-%d %H:%M:%S")
            else:
                ts = raw_ts

            avg_score = float(r.avg_risk_score) if r.avg_risk_score is not None else 0.0
            buckets.append(
                {
                    "timestamp": ts,
                    "prediction_count": r.prediction_count,
                    "distinct_transactions": r.distinct_transactions,
                    "predicted_fraud_count": r.predicted_fraud_count,
                    "predicted_legitimate_count": r.predicted_legitimate_count,
                    "high_risk_count": r.high_risk_count,
                    "average_risk_score": round(avg_score, 2),
                }
            )

        return buckets

    @staticmethod
    def get_case_status_distribution(
        db: Session,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Aggregate investigation cases by status and compute resolution metrics."""
        # 1. Status breakdown
        status_stmt = select(
            InvestigationCase.status,
            func.count(InvestigationCase.id).label("status_count"),
        ).group_by(InvestigationCase.status)
        if start_date is not None:
            status_stmt = status_stmt.where(InvestigationCase.created_at >= start_date)
        if end_date is not None:
            status_stmt = status_stmt.where(InvestigationCase.created_at <= end_date)

        status_rows = db.execute(status_stmt).all()
        status_map = {row.status: row.status_count for row in status_rows}

        # 2. Summary & average resolution time
        is_pg = db.bind is not None and db.bind.dialect.name == "postgresql"
        if is_pg:
            time_diff = extract("epoch", InvestigationCase.resolved_at - InvestigationCase.created_at)
        else:
            time_diff = (
                func.julianday(InvestigationCase.resolved_at) - func.julianday(InvestigationCase.created_at)
            ) * 86400.0

        summary_stmt = select(
            func.count(InvestigationCase.id).label("total_cases"),
            func.count().filter(InvestigationCase.assigned_user_id.is_not(None)).label("assigned_count"),
            func.count().filter(InvestigationCase.assigned_user_id.is_(None)).label("unassigned_count"),
            func.count().filter(InvestigationCase.status.in_(["OPEN", "IN_REVIEW"])).label("unresolved_count"),
            func.count().filter(InvestigationCase.status == "CONFIRMED_FRAUD").label("resolved_fraud_count"),
            func.count().filter(InvestigationCase.status == "LEGITIMATE").label("resolved_legitimate_count"),
            func.avg(time_diff).filter(InvestigationCase.resolved_at.is_not(None)).label("avg_resolution_seconds"),
        )
        if start_date is not None:
            summary_stmt = summary_stmt.where(InvestigationCase.created_at >= start_date)
        if end_date is not None:
            summary_stmt = summary_stmt.where(InvestigationCase.created_at <= end_date)

        summary_row = db.execute(summary_stmt).first()
        total_cases = summary_row.total_cases if summary_row else 0
        assigned_count = summary_row.assigned_count if summary_row else 0
        unassigned_count = summary_row.unassigned_count if summary_row else 0
        unresolved_count = summary_row.unresolved_count if summary_row else 0
        resolved_fraud = summary_row.resolved_fraud_count if summary_row else 0
        resolved_legit = summary_row.resolved_legitimate_count if summary_row else 0
        raw_res_time = summary_row.avg_resolution_seconds if summary_row else None
        avg_res_time = round(float(raw_res_time), 2) if raw_res_time is not None else None

        items = []
        ordered_statuses = ["OPEN", "IN_REVIEW", "CONFIRMED_FRAUD", "LEGITIMATE", "CLOSED"]
        for st in ordered_statuses:
            c = status_map.get(st, 0)
            pct = round((c / total_cases) * 100.0, 2) if total_cases > 0 else 0.0
            items.append({"status": st, "count": c, "percentage": pct})

        return {
            "total_cases": total_cases,
            "items": items,
            "summary": {
                "assigned_count": assigned_count,
                "unassigned_count": unassigned_count,
                "unresolved_count": unresolved_count,
                "resolved_fraud_count": resolved_fraud,
                "resolved_legitimate_count": resolved_legit,
                "average_resolution_time_seconds": avg_res_time,
            },
        }

    @staticmethod
    def get_feature_importance_explanations(
        db: Session,
        risk_level: str | None = "HIGH",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        sample_limit: int = 100,
    ) -> list[Any]:
        """Retrieve bounded sample of latest prediction explanations for feature importance aggregation."""
        lp = AnalyticsRepository.get_latest_predictions_subquery(start_date, end_date)
        stmt = (
            select(lp.c.explanation)
            .where(lp.c.rn == 1)
            .where(lp.c.explanation.is_not(None))
        )
        if risk_level is not None:
            stmt = stmt.where(lp.c.risk_level == risk_level.upper())

        stmt = stmt.order_by(lp.c.predicted_at.desc(), lp.c.id.desc()).limit(sample_limit)
        return list(db.scalars(stmt).all())
