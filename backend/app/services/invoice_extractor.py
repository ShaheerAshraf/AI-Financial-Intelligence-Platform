from sqlalchemy.orm import Session

from app.agents.base import generate_structured
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceExtraction

EXTRACTION_STATUS_PENDING = "PENDING"
EXTRACTION_STATUS_EXTRACTED = "EXTRACTED"
EXTRACTION_STATUS_FAILED = "FAILED"

SYSTEM_INSTRUCTIONS = """
You are an invoice data extraction system.

Your only job is to read raw OCR text from an invoice and extract structured fields.

Extract only what is explicitly present in the OCR text.
Do not invent invoice numbers, vendors, dates, amounts, or descriptions.

Return JSON with these fields:
- invoice_number
- vendor_name
- invoice_date (ISO format YYYY-MM-DD if present)
- due_date (ISO format YYYY-MM-DD if present)
- amount (numeric total amount only, no currency symbols)
- currency (3-letter code such as EUR, USD)
- description (brief service or line-item summary if present)

Use null for any field that cannot be determined from the OCR text.
""".strip()


def extract_invoice(raw_ocr_text: str) -> InvoiceExtraction:
    """
    Extract structured invoice data from raw OCR text.

    Answers: "What does this invoice say?"
    """
    return generate_structured(
        system_instruction=SYSTEM_INSTRUCTIONS,
        user_content=raw_ocr_text,
        response_model=InvoiceExtraction,
    )


def apply_extraction(invoice: Invoice, extraction: InvoiceExtraction) -> None:
    """Write extracted fields onto an Invoice ORM instance."""
    invoice.invoice_number = extraction.invoice_number
    invoice.vendor_name = extraction.vendor_name
    invoice.invoice_date = extraction.invoice_date
    invoice.due_date = extraction.due_date
    invoice.amount = extraction.amount
    invoice.currency = extraction.currency
    invoice.description = extraction.description
    invoice.extraction_status = EXTRACTION_STATUS_EXTRACTED
    invoice.extraction_error = None


def extract_and_persist(db: Session, invoice: Invoice) -> InvoiceExtraction:
    """
    Run extraction for one invoice row and update PostgreSQL.

    Sets extraction_status to EXTRACTED or FAILED.
    """
    try:
        extraction = extract_invoice(invoice.raw_ocr_text)
        apply_extraction(invoice, extraction)
        db.commit()
        db.refresh(invoice)
        return extraction
    except Exception as exc:
        invoice.extraction_status = EXTRACTION_STATUS_FAILED
        invoice.extraction_error = str(exc)[:2000]
        db.commit()
        raise


def run_pending_extractions(db: Session, *, limit: int | None = None) -> dict[str, int]:
    """
    Process invoices with extraction_status == PENDING.

    Returns counts: processed, extracted, failed.
    """
    query = (
        db.query(Invoice)
        .filter(Invoice.extraction_status == EXTRACTION_STATUS_PENDING)
        .order_by(Invoice.id.asc())
    )
    if limit is not None:
        query = query.limit(limit)

    invoices = query.all()
    extracted = 0
    failed = 0

    for invoice in invoices:
        try:
            extract_and_persist(db, invoice)
            extracted += 1
        except Exception:
            failed += 1

    return {
        "processed": len(invoices),
        "extracted": extracted,
        "failed": failed,
    }
