from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.agents.review_agent import AGENT_VERSION
from app.db.database import get_db
from app.models.anomaly_result import AnomalyResult
from app.models.financial_review import FinancialReview
from app.models.invoice_verification import InvoiceVerification
from app.models.transaction import Transaction
from app.schemas.financial_review import (
    AnomalyTrendPoint,
    DashboardOverviewResponse,
    DashboardSummaryResponse,
    RecentHighRiskItem,
    RecentReviewItem,
    RiskDistributionItem,
)

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
)

MISMATCH_STATUSES = {
    "AMOUNT_MISMATCH",
    "VENDOR_MISMATCH",
    "DATE_MISMATCH",
    "MULTIPLE_MISMATCHES",
}


def _build_summary(db: Session) -> DashboardSummaryResponse:
    total_transactions = db.query(Transaction).count()
    total_anomalies = db.query(AnomalyResult).count()
    high_risk_transactions = (
        db.query(AnomalyResult)
        .filter(AnomalyResult.status == "HIGH")
        .count()
    )
    invoice_mismatches = (
        db.query(InvoiceVerification)
        .filter(InvoiceVerification.match_status.in_(MISMATCH_STATUSES))
        .count()
    )
    manual_reviews = (
        db.query(FinancialReview)
        .filter(
            FinancialReview.agent_version == AGENT_VERSION,
            FinancialReview.decision == "MANUAL_REVIEW",
        )
        .count()
    )
    pending_reviews = (
        db.query(FinancialReview)
        .filter(
            FinancialReview.agent_version == AGENT_VERSION,
            FinancialReview.review_status == "PENDING",
        )
        .count()
    )

    return DashboardSummaryResponse(
        total_transactions=total_transactions,
        total_anomalies=total_anomalies,
        high_risk_transactions=high_risk_transactions,
        pending_reviews=pending_reviews,
        invoice_mismatches=invoice_mismatches,
        manual_reviews=manual_reviews,
    )


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    db: Session = Depends(get_db),
):
    return _build_summary(db)


@router.get("/overview", response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    db: Session = Depends(get_db),
):
    summary = _build_summary(db)

    trend_rows = (
        db.query(
            func.date(AnomalyResult.detected_at).label("day"),
            func.count(AnomalyResult.id).label("count"),
        )
        .group_by(func.date(AnomalyResult.detected_at))
        .order_by(func.date(AnomalyResult.detected_at).asc())
        .all()
    )
    anomaly_trend = [
        AnomalyTrendPoint(date=row.day, count=row.count)
        for row in trend_rows
    ]

    distribution_rows = (
        db.query(AnomalyResult.status, func.count(AnomalyResult.id))
        .group_by(AnomalyResult.status)
        .all()
    )
    risk_distribution = [
        RiskDistributionItem(status=status, count=count)
        for status, count in distribution_rows
    ]

    recent_high_risk_rows = (
        db.query(AnomalyResult, Transaction)
        .join(Transaction, Transaction.id == AnomalyResult.transaction_id)
        .options(joinedload(Transaction.vendor))
        .filter(AnomalyResult.status == "HIGH")
        .order_by(AnomalyResult.anomaly_score.asc())
        .limit(10)
        .all()
    )
    recent_high_risk = [
        RecentHighRiskItem(
            transaction_id=transaction.id,
            amount=transaction.amount,
            vendor_id=transaction.vendor_id,
            category_id=transaction.category_id,
            vendor_name=transaction.vendor.name if transaction.vendor else None,
            anomaly_score=anomaly.anomaly_score,
            status=anomaly.status,
            transaction_date=transaction.transaction_date,
        )
        for anomaly, transaction in recent_high_risk_rows
    ]

    recent_review_rows = (
        db.query(FinancialReview, Transaction)
        .join(Transaction, Transaction.id == FinancialReview.transaction_id)
        .filter(FinancialReview.agent_version == AGENT_VERSION)
        .order_by(FinancialReview.created_at.desc())
        .limit(10)
        .all()
    )
    recent_reviews = [
        RecentReviewItem(
            transaction_id=transaction.id,
            amount=transaction.amount,
            final_risk=review.final_risk_level,
            decision=review.decision,
            review_status=review.review_status,
            created_at=review.created_at,
        )
        for review, transaction in recent_review_rows
    ]

    return DashboardOverviewResponse(
        summary=summary,
        anomaly_trend=anomaly_trend,
        risk_distribution=risk_distribution,
        recent_high_risk=recent_high_risk,
        recent_reviews=recent_reviews,
    )
