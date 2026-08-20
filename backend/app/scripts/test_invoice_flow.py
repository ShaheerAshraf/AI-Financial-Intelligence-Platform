"""
End-to-end invoice flow scenarios A/B/C.

Run from backend/:
  python -m app.scripts.test_invoice_flow
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.db.database import SessionLocal
from app.models.anomaly_result import AnomalyResult
from app.models.financial_review import FinancialReview
from app.models.invoice import Invoice
from app.models.invoice_verification import InvoiceVerification
from app.models.transaction import Transaction
from app.models.transaction_analysis import TransactionAnalysis
from app.models.vendor import Vendor
from app.agents.invoice_verification_runner import run_verification_for_transaction
from app.services.financial_investigation import build_investigation
from app.workflows.financial_workflow import run_financial_workflow


def _clear_pipeline(db, transaction_id: int, *, keep_anomaly: bool = True) -> None:
    db.query(FinancialReview).filter(
        FinancialReview.transaction_id == transaction_id
    ).delete(synchronize_session=False)
    db.query(InvoiceVerification).filter(
        InvoiceVerification.transaction_id == transaction_id
    ).delete(synchronize_session=False)
    db.query(TransactionAnalysis).filter(
        TransactionAnalysis.transaction_id == transaction_id
    ).delete(synchronize_session=False)
    db.query(Invoice).filter(Invoice.transaction_id == transaction_id).delete(
        synchronize_session=False
    )
    if not keep_anomaly:
        db.query(AnomalyResult).filter(
            AnomalyResult.transaction_id == transaction_id
        ).delete(synchronize_session=False)
    txn = db.get(Transaction, transaction_id)
    if txn:
        txn.analysis_status = "NEW"
    db.commit()


def _ensure_low_anomaly(db, transaction_id: int) -> None:
    existing = (
        db.query(AnomalyResult)
        .filter(AnomalyResult.transaction_id == transaction_id)
        .first()
    )
    if existing:
        existing.status = "LOW"
        existing.anomaly_score = 0.05
        existing.reason = "Within normal vendor and category spending range"
        existing.model_version = "test_low_v1"
    else:
        db.add(
            AnomalyResult(
                transaction_id=transaction_id,
                anomaly_score=0.05,
                status="LOW",
                reason="Within normal vendor and category spending range",
                model_version="test_low_v1",
                detected_at=datetime.utcnow(),
            )
        )
    db.commit()


def _print_investigation(db, transaction_id: int, label: str) -> None:
    txn = db.get(Transaction, transaction_id)
    inv = build_investigation(db, txn)
    print(f"\n=== {label} (txn #{transaction_id}) ===")
    print(f"  anomaly: {inv.anomaly.status if inv.anomaly else None}")
    print(
        f"  agent1: {inv.transaction_analysis.risk_level if inv.transaction_analysis else None}"
    )
    print(
        f"  invoice: {inv.invoice.invoice_number if inv.invoice else 'none'} "
        f"amount={inv.invoice.amount if inv.invoice else None}"
    )
    print(
        f"  agent2: {inv.invoice_verification.status if inv.invoice_verification else None}"
    )
    if inv.invoice_verification and inv.invoice_verification.field_comparisons:
        for item in inv.invoice_verification.field_comparisons:
            print(
                f"    {item.label}: {item.status} "
                f"({item.transaction_value} vs {item.invoice_value})"
            )
    print(
        f"  agent3: risk={inv.financial_review.risk_level if inv.financial_review else None} "
        f"decision={inv.financial_review.decision if inv.financial_review else None}"
    )


def test_a_normal_no_invoice(db) -> int:
    # Prefer a small non-HIGH transaction
    txn = (
        db.query(Transaction)
        .outerjoin(AnomalyResult, AnomalyResult.transaction_id == Transaction.id)
        .filter(
            (AnomalyResult.status.is_(None)) | (AnomalyResult.status != "HIGH")
        )
        .order_by(Transaction.amount.asc())
        .first()
    )
    assert txn is not None
    _clear_pipeline(db, txn.id, keep_anomaly=False)
    _ensure_low_anomaly(db, txn.id)

    # Agent 2 alone (NOT_PROVIDED) then full workflow
    v = run_verification_for_transaction(db, txn.id)
    assert v.match_status == "NOT_PROVIDED", v.match_status

    result = run_financial_workflow(db, txn.id)
    print(f"Test A workflow status: {result.get('workflow_status')}")
    if result.get("error"):
        print(f"  error: {result['error']}")
    _print_investigation(db, txn.id, "Test A — normal, no invoice")
    return txn.id


def test_b_suspicious_no_invoice(db) -> int:
    txn_id = 3027
    _clear_pipeline(db, txn_id, keep_anomaly=True)
    v = run_verification_for_transaction(db, txn_id)
    assert v.match_status == "NOT_PROVIDED", v.match_status

    result = run_financial_workflow(db, txn_id)
    print(f"Test B workflow status: {result.get('workflow_status')}")
    if result.get("error"):
        print(f"  error: {result['error']}")
    _print_investigation(db, txn_id, "Test B — suspicious, no invoice")
    return txn_id


def test_c_suspicious_mismatch_invoice(db) -> int:
    txn_id = 3028
    _clear_pipeline(db, txn_id, keep_anomaly=True)
    txn = db.get(Transaction, txn_id)
    vendor_name = (
        db.query(Vendor.name).filter(Vendor.id == txn.vendor_id).scalar()
        if txn and txn.vendor_id
        else "Vendor 41"
    )

    # Mismatching invoice (amount much lower)
    invoice = Invoice(
        transaction_id=txn_id,
        invoice_number="INV-2026-0192",
        vendor_name=vendor_name,
        amount=Decimal("95000.00"),
        currency=txn.currency if txn else "EUR",
        invoice_date=txn.transaction_date if txn else None,
        raw_ocr_text=(
            f"Invoice Number: INV-2026-0192\n"
            f"Vendor: {vendor_name}\n"
            f"Amount: 95000.00 EUR\n"
            f"Date: {txn.transaction_date if txn else ''}"
        ),
        extraction_status="EXTRACTED",
    )
    db.add(invoice)
    db.commit()

    v = run_verification_for_transaction(db, txn_id)
    assert v.match_status in {
        "AMOUNT_MISMATCH",
        "MULTIPLE_MISMATCHES",
    }, v.match_status
    assert any(
        c.get("field") == "amount" and c.get("status") == "MISMATCH"
        for c in (v.field_comparisons or [])
    )

    result = run_financial_workflow(db, txn_id)
    print(f"Test C workflow status: {result.get('workflow_status')}")
    if result.get("error"):
        print(f"  error: {result['error']}")
    _print_investigation(db, txn_id, "Test C — suspicious + mismatch invoice")
    return txn_id


def main() -> None:
    db = SessionLocal()
    try:
        print("Running invoice flow scenarios...")
        test_a_normal_no_invoice(db)
        test_b_suspicious_no_invoice(db)
        test_c_suspicious_mismatch_invoice(db)
        print("\nDone.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
