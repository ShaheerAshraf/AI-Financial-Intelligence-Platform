from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.agents.invoice_agent import AGENT_VERSION as INVOICE_AGENT_VERSION
from app.db.database import get_db
from app.models.invoice import Invoice
from app.models.invoice_verification import InvoiceVerification
from app.models.transaction import Transaction
from app.schemas.financial_review import InvoiceListItem, PaginatedInvoicesResponse
from app.schemas.invoice_api import InvoiceCreate, InvoiceResponse, InvoiceUploadResponse
from app.services.invoice_extractor import (
    EXTRACTION_STATUS_PENDING,
    apply_extraction,
    extract_invoice,
)


router = APIRouter(
    prefix="/api/invoices",
    tags=["Invoices"],
)


def _latest_match_status(db: Session, invoice: Invoice) -> str | None:
    verification = (
        db.query(InvoiceVerification)
        .filter(
            InvoiceVerification.invoice_id == invoice.id,
            InvoiceVerification.agent_version == INVOICE_AGENT_VERSION,
        )
        .order_by(InvoiceVerification.created_at.desc())
        .first()
    )
    if verification:
        return verification.match_status
    # Fall back to any verification on the transaction
    verification = (
        db.query(InvoiceVerification)
        .filter(
            InvoiceVerification.transaction_id == invoice.transaction_id,
            InvoiceVerification.agent_version == INVOICE_AGENT_VERSION,
        )
        .order_by(InvoiceVerification.created_at.desc())
        .first()
    )
    return verification.match_status if verification else None


@router.get("/", response_model=PaginatedInvoicesResponse)
def list_invoices(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    transaction_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Invoice)
    if transaction_id is not None:
        query = query.filter(Invoice.transaction_id == transaction_id)

    total = query.count()
    pages = ceil(total / limit) if total else 0

    invoices = (
        query.order_by(Invoice.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    items = [
        InvoiceListItem(
            id=invoice.id,
            transaction_id=invoice.transaction_id,
            invoice_number=invoice.invoice_number,
            vendor_name=invoice.vendor_name,
            amount=invoice.amount,
            currency=invoice.currency,
            invoice_date=invoice.invoice_date,
            extraction_status=invoice.extraction_status,
            match_status=_latest_match_status(db, invoice),
        )
        for invoice in invoices
    ]

    return PaginatedInvoicesResponse(
        items=items,
        page=page,
        limit=limit,
        total=total,
        pages=pages,
    )


@router.post("/", response_model=InvoiceUploadResponse, status_code=201)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
):
    transaction = db.get(Transaction, payload.transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    invoice = Invoice(
        transaction_id=payload.transaction_id,
        raw_ocr_text=payload.raw_ocr_text.strip(),
        ocr_confidence=payload.ocr_confidence,
        extraction_status=EXTRACTION_STATUS_PENDING,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    extraction = None
    if payload.run_extraction:
        try:
            extraction = extract_invoice(invoice.raw_ocr_text)
            apply_extraction(invoice, extraction)
            db.commit()
            db.refresh(invoice)
        except Exception as exc:
            invoice.extraction_status = "FAILED"
            invoice.extraction_error = str(exc)[:2000]
            db.commit()
            db.refresh(invoice)

    return InvoiceUploadResponse(
        invoice=InvoiceResponse.model_validate(invoice),
        extraction=extraction,
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice
