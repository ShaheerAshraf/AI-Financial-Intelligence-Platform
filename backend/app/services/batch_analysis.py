"""
Batch analysis: claim NEW transactions, lock as ANALYZING, run workflow, record runs.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.analysis_run import AnalysisRun, AnalysisRunItem
from app.models.anomaly_result import AnomalyResult
from app.models.transaction import Transaction
from app.workflows.financial_workflow import run_financial_workflow

STATUS_NEW = "NEW"
STATUS_ANALYZING = "ANALYZING"
STATUS_ANALYZED = "ANALYZED"
STATUS_FAILED = "ANALYSIS_FAILED"


def count_new_transactions(db: Session) -> int:
    return (
        db.query(Transaction)
        .filter(Transaction.analysis_status == STATUS_NEW)
        .count()
    )


def claim_new_transactions(
    db: Session,
    *,
    limit: int = 10,
    mode: str = "NEW",
) -> AnalysisRun:
    """
    Atomically select newest NEW transactions and mark them ANALYZING.

    Uses FOR UPDATE SKIP LOCKED so concurrent Analyze New clicks cannot
    claim the same rows.
    """
    rows = db.execute(
        text(
            """
            SELECT id
            FROM transactions
            WHERE analysis_status = :status_new
            ORDER BY id DESC
            LIMIT :limit
            FOR UPDATE SKIP LOCKED
            """
        ),
        {"status_new": STATUS_NEW, "limit": limit},
    ).fetchall()

    transaction_ids = [row[0] for row in rows]

    run = AnalysisRun(
        started_at=datetime.utcnow(),
        mode=mode,
        status="RUNNING",
        batch_size=limit,
        total_transactions=len(transaction_ids),
        successful=0,
        failed=0,
        high_risk=0,
        medium_risk=0,
        low_risk=0,
    )
    db.add(run)
    db.flush()

    for txn_id in transaction_ids:
        txn = db.get(Transaction, txn_id)
        if txn is None:
            continue
        txn.analysis_status = STATUS_ANALYZING
        db.add(
            AnalysisRunItem(
                run_id=run.id,
                transaction_id=txn_id,
                status="PENDING",
            )
        )

    db.commit()
    db.refresh(run)
    return run


def _latest_risk(db: Session, transaction_id: int) -> str | None:
    anomaly = (
        db.query(AnomalyResult)
        .filter(AnomalyResult.transaction_id == transaction_id)
        .order_by(AnomalyResult.detected_at.desc())
        .first()
    )
    return anomaly.status if anomaly else None


def process_run_item(
    db: Session,
    *,
    run_id: int,
    transaction_id: int,
) -> AnalysisRunItem:
    """Run workflow for one claimed transaction and update run item + status."""
    item = (
        db.query(AnalysisRunItem)
        .filter(
            AnalysisRunItem.run_id == run_id,
            AnalysisRunItem.transaction_id == transaction_id,
        )
        .first()
    )
    if item is None:
        raise ValueError(
            f"Transaction {transaction_id} is not part of analysis run {run_id}"
        )

    txn = db.get(Transaction, transaction_id)
    if txn is None:
        raise ValueError(f"Transaction {transaction_id} not found")

    item.status = "RUNNING"
    item.started_at = datetime.utcnow()
    if txn.analysis_status != STATUS_ANALYZING:
        txn.analysis_status = STATUS_ANALYZING
    db.commit()

    try:
        result = run_financial_workflow(db, transaction_id)
        workflow_status = result.get("workflow_status", "UNKNOWN")
        error = result.get("error")

        # Refresh after workflow commit
        txn = db.get(Transaction, transaction_id)
        item = (
            db.query(AnalysisRunItem)
            .filter(AnalysisRunItem.id == item.id)
            .one()
        )

        if workflow_status in {"COMPLETED", "NORMAL"}:
            item.status = "SUCCESS" if workflow_status == "COMPLETED" else "NORMAL"
            if txn:
                txn.analysis_status = STATUS_ANALYZED
        else:
            item.status = "FAILED"
            item.error = error
            if txn:
                txn.analysis_status = STATUS_FAILED

        item.workflow_status = workflow_status
        item.risk_level = _latest_risk(db, transaction_id)
        item.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(item)
        return item
    except Exception as exc:
        db.rollback()
        txn = db.get(Transaction, transaction_id)
        item = (
            db.query(AnalysisRunItem)
            .filter(
                AnalysisRunItem.run_id == run_id,
                AnalysisRunItem.transaction_id == transaction_id,
            )
            .one()
        )
        item.status = "FAILED"
        item.workflow_status = "FAILED"
        item.error = str(exc)
        item.completed_at = datetime.utcnow()
        if txn:
            txn.analysis_status = STATUS_FAILED
        db.commit()
        db.refresh(item)
        return item


def finalize_run(db: Session, run_id: int) -> AnalysisRun:
    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise ValueError(f"Analysis run {run_id} not found")

    items = (
        db.query(AnalysisRunItem)
        .filter(AnalysisRunItem.run_id == run_id)
        .all()
    )

    successful = sum(1 for i in items if i.status in {"SUCCESS", "NORMAL"})
    failed = sum(1 for i in items if i.status == "FAILED")
    high_risk = sum(1 for i in items if (i.risk_level or "").upper() == "HIGH")
    medium_risk = sum(1 for i in items if (i.risk_level or "").upper() == "MEDIUM")
    low_risk = sum(1 for i in items if (i.risk_level or "").upper() == "LOW")

    run.successful = successful
    run.failed = failed
    run.high_risk = high_risk
    run.medium_risk = medium_risk
    run.low_risk = low_risk
    run.total_transactions = len(items)
    run.remaining_new_after = count_new_transactions(db)
    run.completed_at = datetime.utcnow()
    run.status = "COMPLETED" if failed == 0 else ("PARTIAL" if successful else "FAILED")
    db.commit()
    db.refresh(run)
    return run


def run_batch_analysis(
    db: Session,
    *,
    limit: int = 10,
    mode: str = "NEW",
) -> AnalysisRun:
    """
    Claim up to `limit` NEW transactions, process each, finalize the run.
    """
    run = claim_new_transactions(db, limit=limit, mode=mode)
    items = (
        db.query(AnalysisRunItem)
        .filter(AnalysisRunItem.run_id == run.id)
        .order_by(AnalysisRunItem.id.asc())
        .all()
    )
    for item in items:
        process_run_item(db, run_id=run.id, transaction_id=item.transaction_id)
    return finalize_run(db, run.id)


def mark_transaction_analyzing(db: Session, transaction_id: int) -> Transaction:
    txn = db.get(Transaction, transaction_id)
    if txn is None:
        raise ValueError(f"Transaction {transaction_id} not found")
    if txn.analysis_status == STATUS_ANALYZING:
        return txn
    if txn.analysis_status not in {STATUS_NEW, STATUS_FAILED, STATUS_ANALYZED}:
        # allow re-run of analyzed
        pass
    txn.analysis_status = STATUS_ANALYZING
    db.commit()
    db.refresh(txn)
    return txn
