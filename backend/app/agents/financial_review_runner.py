import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.agents.invoice_agent import AGENT_VERSION as INVOICE_AGENT_VERSION
from app.agents.review_agent import AGENT_VERSION, review_transaction
from app.agents.transaction_agent import AGENT_VERSION as TRANSACTION_AGENT_VERSION
from app.models.anomaly_result import AnomalyResult
from app.models.financial_review import FinancialReview
from app.models.invoice import Invoice
from app.models.invoice_verification import InvoiceVerification
from app.models.transaction import Transaction
from app.models.transaction_analysis import TransactionAnalysis
from app.services.invoice_extractor import EXTRACTION_STATUS_EXTRACTED


def build_review_evidence(
    transaction: Transaction,
    anomaly: AnomalyResult,
    analysis: TransactionAnalysis,
    invoice_verifications: list[InvoiceVerification],
    invoices: list[Invoice],
) -> str:
    """Build structured JSON context for Agent 3."""
    primary_verification = invoice_verifications[0] if invoice_verifications else None
    primary_invoice = invoices[0] if invoices else None

    if primary_verification:
        verification_payload = {
            "status": primary_verification.match_status,
            "summary": primary_verification.summary,
            "mismatches": primary_verification.mismatches or [],
            "field_comparisons": primary_verification.field_comparisons or [],
            "recommendation": primary_verification.recommendation,
        }
    else:
        verification_payload = {
            "status": "NOT_PROVIDED",
            "summary": "Invoice status: NOT PROVIDED",
            "mismatches": [],
            "field_comparisons": [],
            "recommendation": "No invoice attached to this transaction",
        }

    payload = {
        "transaction": {
            "id": transaction.id,
            "amount": float(transaction.amount),
            "vendor_id": transaction.vendor_id,
            "category_id": transaction.category_id,
            "date": transaction.transaction_date.isoformat(),
            "currency": transaction.currency,
            "description": transaction.description,
        },
        "anomaly": {
            "score": anomaly.anomaly_score,
            "status": anomaly.status,
            "reason": anomaly.reason,
            "model_version": anomaly.model_version,
        },
        "transaction_analysis": {
            "risk_level": analysis.risk_level,
            "summary": analysis.summary,
            "findings": analysis.findings,
            "recommendation": analysis.recommendation,
        },
        "invoice_verification": verification_payload,
        "invoice": {
            "id": primary_invoice.id if primary_invoice else None,
            "invoice_number": primary_invoice.invoice_number if primary_invoice else None,
            "vendor_name": primary_invoice.vendor_name if primary_invoice else None,
            "amount": float(primary_invoice.amount) if primary_invoice and primary_invoice.amount is not None else None,
            "invoice_date": primary_invoice.invoice_date.isoformat() if primary_invoice and primary_invoice.invoice_date else None,
            "currency": primary_invoice.currency if primary_invoice else None,
            "ocr_confidence": primary_invoice.ocr_confidence if primary_invoice else None,
            "extraction_status": primary_invoice.extraction_status if primary_invoice else None,
            "provided": primary_invoice is not None,
        },
    }

    if len(invoice_verifications) > 1:
        payload["additional_invoice_verifications"] = [
            {
                "invoice_id": v.invoice_id,
                "status": v.match_status,
                "summary": v.summary,
                "mismatches": v.mismatches,
            }
            for v in invoice_verifications[1:]
        ]

    if len(invoices) > 1:
        payload["additional_invoices"] = [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "amount": float(inv.amount) if inv.amount is not None else None,
                "vendor_name": inv.vendor_name,
            }
            for inv in invoices[1:]
        ]

    return json.dumps(payload, indent=2, default=str)


def save_financial_review(
    db: Session,
    *,
    transaction_id: int,
    result,
    agent_version: str = AGENT_VERSION,
) -> FinancialReview:
    """Replace prior review for this transaction/agent_version, then insert."""
    db.query(FinancialReview).filter(
        FinancialReview.transaction_id == transaction_id,
        FinancialReview.agent_version == agent_version,
    ).delete(synchronize_session=False)

    row = FinancialReview(
        transaction_id=transaction_id,
        final_risk_level=result.final_risk_level,
        decision=result.decision,
        summary=result.summary,
        findings=result.findings,
        evidence=result.evidence,
        recommendation=result.recommendation,
        review_status="PENDING",
        agent_version=agent_version,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    return row


def _latest_anomaly(db: Session, transaction_id: int) -> AnomalyResult | None:
    return (
        db.query(AnomalyResult)
        .filter(AnomalyResult.transaction_id == transaction_id)
        .order_by(AnomalyResult.detected_at.desc())
        .first()
    )


def _latest_analysis(
    db: Session,
    transaction_id: int,
    agent_version: str = TRANSACTION_AGENT_VERSION,
) -> TransactionAnalysis | None:
    return (
        db.query(TransactionAnalysis)
        .filter(
            TransactionAnalysis.transaction_id == transaction_id,
            TransactionAnalysis.agent_version == agent_version,
        )
        .order_by(TransactionAnalysis.created_at.desc())
        .first()
    )


def get_unreviewed_transactions(
    db: Session,
    *,
    agent_version: str = AGENT_VERSION,
    transaction_agent_version: str = TRANSACTION_AGENT_VERSION,
    invoice_agent_version: str = INVOICE_AGENT_VERSION,
    limit: int | None = None,
) -> list[int]:
    """
    Transaction IDs with anomaly + analysis + invoice verification, not yet reviewed.
    """
    reviewed_ids = {
        row[0]
        for row in db.query(FinancialReview.transaction_id)
        .filter(FinancialReview.agent_version == agent_version)
        .all()
    }

    candidate_ids = [
        row[0]
        for row in (
            db.query(Transaction.id)
            .join(AnomalyResult, AnomalyResult.transaction_id == Transaction.id)
            .join(
                TransactionAnalysis,
                (TransactionAnalysis.transaction_id == Transaction.id)
                & (TransactionAnalysis.agent_version == transaction_agent_version),
            )
            .join(
                InvoiceVerification,
                (InvoiceVerification.transaction_id == Transaction.id)
                & (InvoiceVerification.agent_version == invoice_agent_version),
            )
            .join(
                Invoice,
                (Invoice.transaction_id == Transaction.id)
                & (Invoice.extraction_status == EXTRACTION_STATUS_EXTRACTED),
            )
            .distinct()
            .order_by(Transaction.id.asc())
            .all()
        )
        if row[0] not in reviewed_ids
    ]

    if limit is not None:
        candidate_ids = candidate_ids[:limit]

    return candidate_ids


def run_financial_reviews(
    db: Session,
    *,
    limit: int | None = None,
    agent_version: str = AGENT_VERSION,
    transaction_agent_version: str = TRANSACTION_AGENT_VERSION,
    invoice_agent_version: str = INVOICE_AGENT_VERSION,
) -> dict[str, int]:
    """
    Load transactions with full agent pipeline data, run Agent 3, persist reviews.
    """
    transaction_ids = get_unreviewed_transactions(
        db,
        agent_version=agent_version,
        transaction_agent_version=transaction_agent_version,
        invoice_agent_version=invoice_agent_version,
        limit=limit,
    )

    reviewed = 0
    failed = 0

    for transaction_id in transaction_ids:
        try:
            transaction = db.get(Transaction, transaction_id)
            if transaction is None:
                failed += 1
                continue

            anomaly = _latest_anomaly(db, transaction_id)
            analysis = _latest_analysis(db, transaction_id, transaction_agent_version)
            invoice_verifications = (
                db.query(InvoiceVerification)
                .filter(
                    InvoiceVerification.transaction_id == transaction_id,
                    InvoiceVerification.agent_version == invoice_agent_version,
                )
                .order_by(InvoiceVerification.id.asc())
                .all()
            )
            invoices = (
                db.query(Invoice)
                .filter(
                    Invoice.transaction_id == transaction_id,
                    Invoice.extraction_status == EXTRACTION_STATUS_EXTRACTED,
                )
                .order_by(Invoice.id.asc())
                .all()
            )

            if not anomaly or not analysis or not invoice_verifications or not invoices:
                failed += 1
                print(f"  Skipped transaction {transaction_id}: missing pipeline data")
                continue

            evidence = build_review_evidence(
                transaction,
                anomaly,
                analysis,
                invoice_verifications,
                invoices,
            )
            result = review_transaction(evidence)
            save_financial_review(
                db,
                transaction_id=transaction_id,
                result=result,
                agent_version=agent_version,
            )
            db.commit()
            reviewed += 1
        except Exception as exc:
            db.rollback()
            failed += 1
            print(f"  Failed transaction {transaction_id}: {exc}")

    return {
        "pending": len(transaction_ids),
        "reviewed": reviewed,
        "failed": failed,
    }
