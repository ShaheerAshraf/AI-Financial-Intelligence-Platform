from datetime import date, datetime
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.agents.review_agent import AGENT_VERSION
from app.db.database import get_db
from app.models.financial_review import FinancialReview
from app.models.transaction import Transaction
from app.schemas.financial_review import (
    FinancialInvestigationResponse,
    HumanReviewDecision,
    PaginatedReviewsResponse,
)
from app.services.financial_investigation import (
    build_investigation,
    build_review_list_item,
)


router = APIRouter(
    prefix="/api/reviews",
    tags=["Reviews"],
)


@router.get("/", response_model=PaginatedReviewsResponse)
def list_reviews(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = (
        db.query(FinancialReview, Transaction)
        .join(Transaction, Transaction.id == FinancialReview.transaction_id)
        .options(
            joinedload(Transaction.vendor),
            joinedload(Transaction.category),
        )
        .filter(FinancialReview.agent_version == AGENT_VERSION)
        .order_by(FinancialReview.created_at.desc())
    )

    total = query.count()
    pages = ceil(total / limit) if total else 0

    rows = (
        query.offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    items = [
        build_review_list_item(db, review, transaction)
        for review, transaction in rows
    ]

    return PaginatedReviewsResponse(
        items=items,
        page=page,
        limit=limit,
        total=total,
        pages=pages,
    )


@router.post(
    "/{transaction_id}/human-decision",
    response_model=FinancialInvestigationResponse,
)
def submit_human_decision(
    transaction_id: int,
    payload: HumanReviewDecision,
    db: Session = Depends(get_db),
):
    review = (
        db.query(FinancialReview)
        .filter(
            FinancialReview.transaction_id == transaction_id,
            FinancialReview.agent_version == AGENT_VERSION,
        )
        .first()
    )
    if not review:
        raise HTTPException(
            status_code=404,
            detail=f"No financial review found for transaction {transaction_id}",
        )

    review.review_status = payload.decision
    review.reviewed_by = payload.reviewed_by
    review.reviewed_at = datetime.utcnow()
    review.review_comment = payload.comment
    # Persist human outcome separately from AI recommendation (`decision`)
    db.commit()

    transaction = db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return build_investigation(db, transaction)


@router.get("/{transaction_id}", response_model=FinancialInvestigationResponse)
def get_review_by_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    transaction = db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction {transaction_id} not found",
        )

    return build_investigation(db, transaction)
