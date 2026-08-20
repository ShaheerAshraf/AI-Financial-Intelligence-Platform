from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.agents.invoice_agent import AGENT_VERSION, verify_invoice
from app.models.invoice import Invoice
from app.models.invoice_verification import InvoiceVerification
from app.models.transaction import Transaction
from app.models.vendor import Vendor
from app.services.invoice_comparison import (
    compute_field_comparisons,
    derive_match_status,
    mismatches_from_comparisons,
)
from app.services.invoice_extractor import EXTRACTION_STATUS_EXTRACTED


def _fmt_amount(amount: Decimal | None, currency: str | None) -> str:
    if amount is None:
        return "N/A"
    cur = currency or "EUR"
    return f"{cur} {float(amount):,.2f}"


def build_field_comparisons(
    transaction: Transaction,
    invoice: Invoice,
    vendor_name: str | None,
) -> list[dict]:
    return compute_field_comparisons(
        transaction_amount=transaction.amount,
        transaction_currency=transaction.currency,
        transaction_date=transaction.transaction_date,
        transaction_vendor_name=vendor_name,
        invoice_amount=invoice.amount,
        invoice_currency=invoice.currency,
        invoice_date=invoice.invoice_date,
        invoice_vendor_name=invoice.vendor_name,
    )


def build_verification_evidence(
    transaction: Transaction,
    invoice: Invoice,
    vendor_name: str | None,
    field_comparisons: list[dict] | None = None,
) -> str:
    """Build comparison input for Agent 2 from transaction + invoice rows."""
    comparisons = field_comparisons or build_field_comparisons(
        transaction, invoice, vendor_name
    )
    comparison_lines = "\n".join(
        f"- {item['label']}: {item['status']} "
        f"(transaction={item['transaction_value']}, invoice={item['invoice_value']})"
        for item in comparisons
    )

    missing_fields = [
        field
        for field, value in {
            "invoice_number": invoice.invoice_number,
            "vendor_name": invoice.vendor_name,
            "invoice_date": invoice.invoice_date,
            "amount": invoice.amount,
            "currency": invoice.currency,
        }.items()
        if value is None
    ]

    return f"""
Transaction:
- Transaction ID: {transaction.id}
- Amount: {_fmt_amount(transaction.amount, transaction.currency)}
- Vendor ID: {transaction.vendor_id}
- Vendor name (from vendors table): {vendor_name or "N/A"}
- Transaction date: {transaction.transaction_date}
- Currency: {transaction.currency}
- Description: {transaction.description or "N/A"}

Extracted invoice (from OCR extraction layer):
- Invoice ID: {invoice.id}
- Invoice number: {invoice.invoice_number or "MISSING"}
- Vendor name: {invoice.vendor_name or "MISSING"}
- Invoice date: {invoice.invoice_date or "MISSING"}
- Due date: {invoice.due_date or "MISSING"}
- Amount: {_fmt_amount(invoice.amount, invoice.currency)}
- Currency: {invoice.currency or "MISSING"}
- Description: {invoice.description or "MISSING"}
- OCR confidence: {invoice.ocr_confidence if invoice.ocr_confidence is not None else "MISSING"}
- Extraction status: {invoice.extraction_status}
- Missing extracted fields: {", ".join(missing_fields) if missing_fields else "none"}

Deterministic field comparisons:
{comparison_lines}

Use the field comparisons above. Prefer AMOUNT_MISMATCH / VENDOR_MISMATCH /
DATE_MISMATCH / MULTIPLE_MISMATCHES / MATCH / INSUFFICIENT_EVIDENCE accordingly.
""".strip()


def save_invoice_verification(
    db: Session,
    *,
    invoice: Invoice,
    transaction: Transaction,
    result,
    field_comparisons: list[dict] | None = None,
    agent_version: str = AGENT_VERSION,
) -> InvoiceVerification:
    """Replace prior verification for this invoice/agent_version, then insert."""
    comparisons = field_comparisons or []

    db.query(InvoiceVerification).filter(
        InvoiceVerification.invoice_id == invoice.id,
        InvoiceVerification.agent_version == agent_version,
    ).delete(synchronize_session=False)

    # Clear any prior NOT_PROVIDED row for this transaction
    db.query(InvoiceVerification).filter(
        InvoiceVerification.transaction_id == transaction.id,
        InvoiceVerification.invoice_id.is_(None),
        InvoiceVerification.agent_version == agent_version,
    ).delete(synchronize_session=False)

    row = InvoiceVerification(
        invoice_id=invoice.id,
        transaction_id=transaction.id,
        match_status=result.match_status,
        summary=result.summary,
        mismatches=result.mismatches or mismatches_from_comparisons(comparisons),
        field_comparisons=comparisons,
        evidence=result.evidence,
        recommendation=result.recommendation,
        agent_version=agent_version,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    return row


def save_not_provided_verification(
    db: Session,
    *,
    transaction: Transaction,
    agent_version: str = AGENT_VERSION,
) -> InvoiceVerification:
    """Persist Agent 2 NOT_PROVIDED when no invoice is attached."""
    db.query(InvoiceVerification).filter(
        InvoiceVerification.transaction_id == transaction.id,
        InvoiceVerification.agent_version == agent_version,
        InvoiceVerification.invoice_id.is_(None),
    ).delete(synchronize_session=False)

    row = InvoiceVerification(
        invoice_id=None,
        transaction_id=transaction.id,
        match_status="NOT_PROVIDED",
        summary="Invoice status: NOT PROVIDED",
        mismatches=[],
        field_comparisons=[],
        evidence=["No invoice attached to this transaction"],
        recommendation="Request invoice documentation if the transaction requires verification",
        agent_version=agent_version,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    return row


def run_verification_for_transaction(
    db: Session,
    transaction_id: int,
    *,
    agent_version: str = AGENT_VERSION,
) -> InvoiceVerification:
    """
    Run Agent 2 for a transaction.

    With invoice → compare fields + LLM verification.
    Without invoice → persist NOT_PROVIDED (does not fail).
    """
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise ValueError(f"Transaction {transaction_id} not found")

    invoice = (
        db.query(Invoice)
        .filter(
            Invoice.transaction_id == transaction_id,
            Invoice.extraction_status == EXTRACTION_STATUS_EXTRACTED,
        )
        .order_by(Invoice.id.desc())
        .first()
    )

    if invoice is None:
        row = save_not_provided_verification(
            db,
            transaction=transaction,
            agent_version=agent_version,
        )
        db.commit()
        db.refresh(row)
        return row

    vendor_name = None
    if transaction.vendor_id:
        vendor_name = (
            db.query(Vendor.name)
            .filter(Vendor.id == transaction.vendor_id)
            .scalar()
        )

    comparisons = build_field_comparisons(transaction, invoice, vendor_name)
    deterministic_status = derive_match_status(comparisons)
    deterministic_mismatches = mismatches_from_comparisons(comparisons)

    try:
        evidence = build_verification_evidence(
            transaction, invoice, vendor_name, comparisons
        )
        result = verify_invoice(evidence)
    except Exception:
        # Fall back to deterministic result if Gemini is unavailable
        result = SimpleNamespace(
            match_status=deterministic_status,
            summary=(
                "Invoice verified using field comparison "
                f"(status={deterministic_status})"
            ),
            mismatches=deterministic_mismatches,
            evidence=[
                f"{item['label']}: {item['status']}" for item in comparisons
            ],
            recommendation=(
                "Investigate mismatched fields before approval"
                if deterministic_status != "MATCH"
                else "Invoice fields match the transaction"
            ),
        )

    # Prefer deterministic status when LLM drifts from clear amount/vendor mismatch
    if deterministic_status in {
        "AMOUNT_MISMATCH",
        "VENDOR_MISMATCH",
        "DATE_MISMATCH",
        "MULTIPLE_MISMATCHES",
        "MATCH",
    }:
        if result.match_status != deterministic_status:
            result = SimpleNamespace(
                match_status=deterministic_status,
                summary=result.summary,
                mismatches=deterministic_mismatches or result.mismatches,
                evidence=result.evidence,
                recommendation=result.recommendation,
            )

    row = save_invoice_verification(
        db,
        invoice=invoice,
        transaction=transaction,
        result=result,
        field_comparisons=comparisons,
        agent_version=agent_version,
    )
    db.commit()
    db.refresh(row)
    return row


def get_unverified_invoices(
    db: Session,
    *,
    agent_version: str = AGENT_VERSION,
    limit: int | None = None,
) -> list[tuple[Invoice, Transaction, str | None]]:
    """
    Invoices with EXTRACTED status and no verification for this agent version.
    """
    verified_ids = {
        row[0]
        for row in db.query(InvoiceVerification.invoice_id)
        .filter(
            InvoiceVerification.agent_version == agent_version,
            InvoiceVerification.invoice_id.isnot(None),
        )
        .all()
    }

    query = (
        db.query(Invoice, Transaction, Vendor.name)
        .join(Transaction, Transaction.id == Invoice.transaction_id)
        .outerjoin(Vendor, Vendor.id == Transaction.vendor_id)
        .filter(Invoice.extraction_status == EXTRACTION_STATUS_EXTRACTED)
        .order_by(Invoice.id.asc())
    )

    rows = query.all()
    pending = [
        (invoice, transaction, vendor_name)
        for invoice, transaction, vendor_name in rows
        if invoice.id not in verified_ids
    ]

    if limit is not None:
        pending = pending[:limit]

    return pending


def run_invoice_verifications(
    db: Session,
    *,
    limit: int | None = None,
    agent_version: str = AGENT_VERSION,
) -> dict[str, int]:
    """
    Load unverified invoices, run Agent 2, persist to invoice_verifications.
    """
    pending = get_unverified_invoices(
        db,
        agent_version=agent_version,
        limit=limit,
    )

    verified = 0
    failed = 0

    for invoice, transaction, _vendor_name in pending:
        try:
            run_verification_for_transaction(
                db,
                transaction.id,
                agent_version=agent_version,
            )
            verified += 1
        except Exception as exc:
            db.rollback()
            failed += 1
            print(f"  Failed invoice {invoice.id}: {exc}")

    return {
        "pending": len(pending),
        "verified": verified,
        "failed": failed,
    }
