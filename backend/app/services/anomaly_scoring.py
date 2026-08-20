"""
Online anomaly scoring for newly created transactions.

Batch ML (`ml/train.py`) only scores rows that existed at training time.
Analyze must score new transactions against historical vendor/category spend.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.anomaly_result import AnomalyResult
from app.models.transaction import Transaction

ONLINE_MODEL_VERSION = "online_historical_v1"


def _avg_std(
    db: Session,
    *,
    column,
    value: int | None,
    exclude_id: int,
) -> tuple[float | None, float | None, int]:
    if value is None:
        return None, None, 0

    rows = (
        db.query(Transaction.amount)
        .filter(column == value, Transaction.id != exclude_id)
        .all()
    )
    amounts = [float(r[0]) for r in rows]
    n = len(amounts)
    if n == 0:
        return None, None, 0

    avg = sum(amounts) / n
    if n < 2:
        return avg, None, n

    var = sum((a - avg) ** 2 for a in amounts) / (n - 1)
    return avg, var**0.5, n


def score_transaction_anomaly(
    db: Session,
    transaction_id: int,
) -> AnomalyResult:
    """
    Score one transaction vs historical vendor/category averages and persist.

    Returns the saved AnomalyResult (HIGH / MEDIUM / NORMAL).
    """
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise ValueError(f"Transaction {transaction_id} not found")

    amount = float(transaction.amount)
    vendor_avg, vendor_std, vendor_n = _avg_std(
        db,
        column=Transaction.vendor_id,
        value=transaction.vendor_id,
        exclude_id=transaction_id,
    )
    category_avg, _category_std, category_n = _avg_std(
        db,
        column=Transaction.category_id,
        value=transaction.category_id,
        exclude_id=transaction_id,
    )

    reasons: list[str] = []
    amount_vs_vendor = (amount / vendor_avg) if vendor_avg and vendor_avg > 0 else None
    amount_vs_category = (
        amount / category_avg if category_avg and category_avg > 0 else None
    )

    if amount_vs_vendor is not None:
        if amount_vs_vendor >= 3:
            reasons.append("Amount much higher than vendor historical average")
        elif amount_vs_vendor >= 2:
            reasons.append("Amount higher than vendor historical average")
        elif amount_vs_vendor <= 0.4:
            reasons.append("Amount much lower than vendor historical average")

    if amount_vs_category is not None:
        if amount_vs_category >= 3:
            reasons.append("Amount much higher than category historical average")
        elif amount_vs_category >= 2:
            reasons.append("Amount higher than category historical average")

    if vendor_std is not None and vendor_avg is not None and vendor_std > 0:
        z_score = abs(amount - vendor_avg) / vendor_std
        if z_score >= 3:
            reasons.append("Outside normal vendor historical spend variation")
    elif (
        vendor_avg is not None
        and vendor_avg > 0
        and abs(amount - vendor_avg) / vendor_avg >= 0.5
        and "Amount much higher than vendor historical average" not in reasons
        and "Amount higher than vendor historical average" not in reasons
    ):
        reasons.append("Unusual amount vs vendor historical average")

    # Extreme absolute amounts with little history still deserve review
    if not reasons and amount >= 1_000_000:
        reasons.append("Extremely large absolute transaction amount")

    if not reasons and vendor_n == 0 and category_n == 0 and amount >= 100_000:
        reasons.append("Large amount with no historical vendor/category data yet")

    if any("much higher" in r or "Outside normal" in r or "Extremely large" in r for r in reasons):
        status = "HIGH"
        # More negative = more anomalous (compatible with Isolation Forest convention)
        score = -0.25
    elif reasons:
        status = "MEDIUM"
        score = -0.08
    else:
        status = "NORMAL"
        score = 0.15
        reasons = ["Within historical vendor/category spending range"]

    # Replace prior online score for this transaction
    db.query(AnomalyResult).filter(
        AnomalyResult.transaction_id == transaction_id,
        AnomalyResult.model_version == ONLINE_MODEL_VERSION,
    ).delete(synchronize_session=False)

    row = AnomalyResult(
        transaction_id=transaction_id,
        anomaly_score=score,
        status=status,
        reason="; ".join(reasons),
        model_version=ONLINE_MODEL_VERSION,
        detected_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
