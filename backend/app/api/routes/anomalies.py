from datetime import date
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.models.anomaly_result import AnomalyResult
from app.models.transaction import Transaction
from app.schemas.anomaly import AnomalyResultResponse, AnomalySummaryResponse
from app.schemas.financial_review import AnomalyListItem, PaginatedAnomaliesResponse


router = APIRouter(
    prefix="/api/anomalies",
    tags=["Anomalies"],
)


@router.get("/", response_model=PaginatedAnomaliesResponse)
def get_anomalies(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: str | None = Query(None),
    vendor_id: int | None = Query(None),
    category_id: int | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be less than or equal to end_date",
        )

    query = (
        db.query(AnomalyResult, Transaction)
        .join(Transaction, Transaction.id == AnomalyResult.transaction_id)
        .options(
            joinedload(Transaction.vendor),
            joinedload(Transaction.category),
        )
    )

    if status:
        query = query.filter(AnomalyResult.status == status.upper())
    if vendor_id is not None:
        query = query.filter(Transaction.vendor_id == vendor_id)
    if category_id is not None:
        query = query.filter(Transaction.category_id == category_id)
    if start_date is not None:
        query = query.filter(Transaction.transaction_date >= start_date)
    if end_date is not None:
        query = query.filter(Transaction.transaction_date <= end_date)

    total = query.count()
    pages = ceil(total / limit) if total else 0

    rows = (
        query.order_by(AnomalyResult.anomaly_score.asc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    items = [
        AnomalyListItem(
            transaction_id=transaction.id,
            amount=transaction.amount,
            vendor_id=transaction.vendor_id,
            category_id=transaction.category_id,
            vendor_name=transaction.vendor.name if transaction.vendor else None,
            category_name=transaction.category.name if transaction.category else None,
            anomaly_score=anomaly.anomaly_score,
            status=anomaly.status,
            reason=anomaly.reason,
            transaction_date=transaction.transaction_date,
        )
        for anomaly, transaction in rows
    ]

    return PaginatedAnomaliesResponse(
        items=items,
        page=page,
        limit=limit,
        total=total,
        pages=pages,
    )


@router.get("/high-risk", response_model=list[AnomalyResultResponse])
def get_high_risk_anomalies(
    db: Session = Depends(get_db),
):
    return (
        db.query(AnomalyResult)
        .filter(AnomalyResult.status == "HIGH")
        .order_by(AnomalyResult.anomaly_score.asc())
        .all()
    )


@router.get("/summary", response_model=AnomalySummaryResponse)
def get_anomaly_summary(
    db: Session = Depends(get_db),
):
    total_transactions = db.query(Transaction).count()
    total_anomalies = db.query(AnomalyResult).count()
    high_risk = (
        db.query(AnomalyResult)
        .filter(AnomalyResult.status == "HIGH")
        .count()
    )
    medium_risk = (
        db.query(AnomalyResult)
        .filter(AnomalyResult.status == "MEDIUM")
        .count()
    )
    anomaly_rate = (
        round((total_anomalies / total_transactions) * 100, 2)
        if total_transactions
        else 0.0
    )

    return AnomalySummaryResponse(
        total_transactions=total_transactions,
        total_anomalies=total_anomalies,
        high_risk=high_risk,
        medium_risk=medium_risk,
        anomaly_rate=anomaly_rate,
    )


@router.get("/{transaction_id}", response_model=AnomalyResultResponse)
def get_anomaly_by_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    anomaly = (
        db.query(AnomalyResult)
        .filter(AnomalyResult.transaction_id == transaction_id)
        .order_by(AnomalyResult.anomaly_score.asc())
        .first()
    )
    if not anomaly:
        raise HTTPException(
            status_code=404,
            detail=f"No anomaly found for transaction_id={transaction_id}",
        )
    return anomaly
