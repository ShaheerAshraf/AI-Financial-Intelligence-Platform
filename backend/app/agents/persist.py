from datetime import datetime

from sqlalchemy.orm import Session

from app.agents.transaction_agent import AGENT_VERSION, analyze_transaction
from app.models.anomaly_result import AnomalyResult
from app.models.transaction import Transaction
from app.models.transaction_analysis import TransactionAnalysis


def build_anomaly_evidence(
    transaction: Transaction,
    anomaly: AnomalyResult,
) -> str:
    """Build evidence text for Agent 1 from DB transaction + anomaly rows."""
    amount = f"€{float(transaction.amount):,.2f}"
    reason_lines = ""
    if anomaly.reason:
        reason_lines = "\n".join(
            f"- {part.strip()}"
            for part in anomaly.reason.split(";")
            if part.strip()
        )

    return f"""
Transaction ID: {transaction.id}
Amount: {amount}
Vendor: {transaction.vendor_id}
Category: {transaction.category_id}
Date: {transaction.transaction_date}
Description: {transaction.description or "N/A"}
Currency: {transaction.currency}

Anomaly score: {anomaly.anomaly_score}
Status: {anomaly.status}
Model version: {anomaly.model_version}
Detected at: {anomaly.detected_at}

Reasons:
{reason_lines or "- No reason provided"}
""".strip()


def save_transaction_analysis(
    db: Session,
    *,
    transaction_id: int,
    analysis,
    agent_version: str = AGENT_VERSION,
) -> TransactionAnalysis:
    """Replace prior analysis for this transaction/agent_version, then insert."""
    db.query(TransactionAnalysis).filter(
        TransactionAnalysis.transaction_id == transaction_id,
        TransactionAnalysis.agent_version == agent_version,
    ).delete(synchronize_session=False)

    row = TransactionAnalysis(
        transaction_id=transaction_id,
        risk_level=analysis.risk_level,
        summary=analysis.summary,
        findings=analysis.findings,
        evidence=analysis.evidence,
        recommendation=analysis.recommendation,
        agent_version=agent_version,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    return row


def run_transaction_analyses(
    db: Session,
    *,
    status: str | None = "HIGH",
    limit: int | None = None,
) -> int:
    """
    Load anomalies from PostgreSQL, run Agent 1, persist to transaction_analyses.

    By default processes HIGH-risk anomalies only.
    Returns number of analyses saved.
    """
    query = (
        db.query(AnomalyResult, Transaction)
        .join(Transaction, Transaction.id == AnomalyResult.transaction_id)
        .order_by(AnomalyResult.anomaly_score.asc())
    )
    if status:
        query = query.filter(AnomalyResult.status == status)
    if limit is not None:
        query = query.limit(limit)

    pairs = query.all()
    saved = 0

    for anomaly, transaction in pairs:
        evidence = build_anomaly_evidence(transaction, anomaly)
        analysis = analyze_transaction(evidence)
        save_transaction_analysis(
            db,
            transaction_id=transaction.id,
            analysis=analysis,
        )
        saved += 1

    db.commit()
    return saved
