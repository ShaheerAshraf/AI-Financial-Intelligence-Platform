import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from math import ceil

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.models.category import Category
from app.models.company import Company
from app.models.transaction import Transaction
from app.models.vendor import Vendor
from app.schemas.transaction import (
    PaginatedTransactionsResponse,
    TransactionCreate,
    TransactionImportResponse,
    TransactionImportRowError,
    TransactionResponse,
    TransactionUpdate,
)
from app.schemas.invoice_api import (
    InvoiceResponse,
    InvoiceUploadResponse,
    InvoiceVerificationResponse,
    TransactionInvoiceCreate,
)
from app.models.invoice import Invoice
from app.agents.invoice_verification_runner import run_verification_for_transaction
from app.services.invoice_extractor import (
    EXTRACTION_STATUS_EXTRACTED,
    EXTRACTION_STATUS_PENDING,
    apply_extraction,
    extract_invoice,
)


router = APIRouter(
    prefix="/api/transactions",
    tags=["Transactions"],
)

CSV_TEMPLATE = (
    "company,vendor,category,amount,currency,transaction_date,description\n"
    "BMW Financial Services,Amazon Web Services,Cloud Services,1250.50,EUR,2026-08-20,Cloud infrastructure\n"
    "BMW Financial Services,Microsoft,Software,830.00,EUR,2026-08-20,Software subscription\n"
)


def _to_response(txn: Transaction) -> TransactionResponse:
    return TransactionResponse(
        id=txn.id,
        company_id=txn.company_id,
        vendor_id=txn.vendor_id,
        category_id=txn.category_id,
        amount=txn.amount,
        currency=txn.currency,
        description=txn.description,
        transaction_date=txn.transaction_date,
        analysis_status=txn.analysis_status,
        company_name=txn.company.name if txn.company else None,
        vendor_name=txn.vendor.name if txn.vendor else None,
        category_name=txn.category.name if txn.category else None,
    )


def _validate_refs(
    db: Session,
    *,
    company_id: int,
    vendor_id: int,
    category_id: int,
) -> tuple[Company, Vendor, Category]:
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    vendor = db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if vendor.company_id != company_id:
        raise HTTPException(
            status_code=400,
            detail="Vendor does not belong to the selected company",
        )

    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if category.company_id != company_id:
        raise HTTPException(
            status_code=400,
            detail="Category does not belong to the selected company",
        )

    return company, vendor, category


def _parse_date(value: str) -> date:
    raw = value.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f'Invalid date "{value}". Use YYYY-MM-DD or DD.MM.YYYY')


def _find_by_name(db: Session, model, name: str, company_id: int | None = None):
    query = db.query(model).filter(model.name.ilike(name.strip()))
    if company_id is not None and hasattr(model, "company_id"):
        query = query.filter(model.company_id == company_id)
    return query.first()


@router.get("/import/template")
def download_csv_template():
    return PlainTextResponse(
        CSV_TEMPLATE,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="transactions_template.csv"',
        },
    )


@router.post("/import", response_model=TransactionImportResponse)
async def import_transactions_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="CSV must be UTF-8 encoded",
        ) from exc

    reader = csv.DictReader(io.StringIO(text))
    required = {"company", "vendor", "category", "amount", "currency", "transaction_date"}
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV is empty or missing header")

    headers = {h.strip().lower() for h in reader.fieldnames if h}
    missing = required - headers
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing columns: {', '.join(sorted(missing))}",
        )

    created_ids: list[int] = []
    errors: list[TransactionImportRowError] = []
    total_rows = 0

    for index, row in enumerate(reader, start=2):
        total_rows += 1
        company_name = (row.get("company") or "").strip()
        vendor_name = (row.get("vendor") or "").strip()
        category_name = (row.get("category") or "").strip()
        amount_raw = (row.get("amount") or "").strip()
        currency = (row.get("currency") or "EUR").strip().upper() or "EUR"
        date_raw = (row.get("transaction_date") or "").strip()
        description = (row.get("description") or "").strip() or None

        try:
            if not company_name:
                raise ValueError("Company is required")
            if not vendor_name:
                raise ValueError("Vendor is required")
            if not category_name:
                raise ValueError("Category is required")

            company = _find_by_name(db, Company, company_name)
            if not company:
                raise ValueError(f'Unknown company: "{company_name}"')

            vendor = _find_by_name(db, Vendor, vendor_name, company.id)
            if not vendor:
                raise ValueError(f'Unknown vendor: "{vendor_name}"')

            category = _find_by_name(db, Category, category_name, company.id)
            if not category:
                raise ValueError(f'Unknown category: "{category_name}"')

            try:
                amount = Decimal(amount_raw.replace(",", ""))
            except (InvalidOperation, AttributeError) as exc:
                raise ValueError(f'Invalid amount: "{amount_raw}"') from exc
            if amount <= 0:
                raise ValueError("Amount must be greater than 0")

            if len(currency) != 3:
                raise ValueError(f'Invalid currency: "{currency}"')

            txn_date = _parse_date(date_raw)

            txn = Transaction(
                company_id=company.id,
                vendor_id=vendor.id,
                category_id=category.id,
                amount=amount,
                currency=currency,
                transaction_date=txn_date,
                description=description,
                analysis_status="NEW",
            )
            db.add(txn)
            db.flush()
            created_ids.append(txn.id)
        except ValueError as exc:
            errors.append(
                TransactionImportRowError(
                    row=index,
                    message=str(exc),
                    company=company_name or None,
                    vendor=vendor_name or None,
                    category=category_name or None,
                )
            )

    if created_ids:
        db.commit()
    else:
        db.rollback()

    return TransactionImportResponse(
        imported=len(created_ids),
        failed=len(errors),
        total_rows=total_rows,
        created_ids=created_ids,
        errors=errors,
    )


@router.post("/", response_model=TransactionResponse, status_code=201)
def create_transaction(
    transaction: TransactionCreate,
    db: Session = Depends(get_db),
):
    _validate_refs(
        db,
        company_id=transaction.company_id,
        vendor_id=transaction.vendor_id,
        category_id=transaction.category_id,
    )

    new_transaction = Transaction(
        company_id=transaction.company_id,
        vendor_id=transaction.vendor_id,
        category_id=transaction.category_id,
        amount=transaction.amount,
        currency=transaction.currency.upper(),
        description=transaction.description,
        transaction_date=transaction.transaction_date,
        analysis_status="NEW",
    )

    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)

    txn = (
        db.query(Transaction)
        .options(
            joinedload(Transaction.company),
            joinedload(Transaction.vendor),
            joinedload(Transaction.category),
        )
        .filter(Transaction.id == new_transaction.id)
        .one()
    )
    return _to_response(txn)


@router.get("/", response_model=PaginatedTransactionsResponse)
def get_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    company_id: int | None = Query(None),
    vendor_id: int | None = Query(None),
    category_id: int | None = Query(None),
    analysis_status: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be less than or equal to end_date",
        )

    query = db.query(Transaction).options(
        joinedload(Transaction.company),
        joinedload(Transaction.vendor),
        joinedload(Transaction.category),
    )

    if company_id is not None:
        query = query.filter(Transaction.company_id == company_id)
    if vendor_id is not None:
        query = query.filter(Transaction.vendor_id == vendor_id)
    if category_id is not None:
        query = query.filter(Transaction.category_id == category_id)
    if analysis_status:
        query = query.filter(Transaction.analysis_status == analysis_status.upper())
    if start_date is not None:
        query = query.filter(Transaction.transaction_date >= start_date)
    if end_date is not None:
        query = query.filter(Transaction.transaction_date <= end_date)

    total = query.count()
    pages = ceil(total / limit) if total else 0

    items = (
        query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return PaginatedTransactionsResponse(
        items=[_to_response(item) for item in items],
        page=page,
        limit=limit,
        total=total,
        pages=pages,
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    txn = (
        db.query(Transaction)
        .options(
            joinedload(Transaction.company),
            joinedload(Transaction.vendor),
            joinedload(Transaction.category),
        )
        .filter(Transaction.id == transaction_id)
        .first()
    )
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return _to_response(txn)


def _latest_invoice(db: Session, transaction_id: int) -> Invoice | None:
    return (
        db.query(Invoice)
        .filter(Invoice.transaction_id == transaction_id)
        .order_by(Invoice.id.desc())
        .first()
    )


def _invoice_response(invoice: Invoice) -> InvoiceResponse:
    return InvoiceResponse.model_validate(invoice)


@router.get(
    "/{transaction_id}/invoice",
    response_model=InvoiceResponse,
)
def get_transaction_invoice(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    transaction = db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    invoice = _latest_invoice(db, transaction_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="No invoice for this transaction")
    return _invoice_response(invoice)


@router.post(
    "/{transaction_id}/invoice",
    response_model=InvoiceUploadResponse,
    status_code=201,
)
def upsert_transaction_invoice(
    transaction_id: int,
    payload: TransactionInvoiceCreate,
    db: Session = Depends(get_db),
):
    """
    Attach or replace invoice OCR/structured data for a transaction.

    PDF/image is never stored — only OCR text + extracted fields.
    """
    transaction = db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    has_structured = any(
        [
            payload.invoice_number,
            payload.vendor_name,
            payload.amount is not None,
            payload.currency,
            payload.invoice_date,
        ]
    )
    if not payload.raw_ocr_text and not has_structured:
        raise HTTPException(
            status_code=400,
            detail="Provide raw_ocr_text and/or structured invoice fields",
        )

    raw_text = (payload.raw_ocr_text or "").strip()
    if not raw_text and has_structured:
        # Synthetic OCR text for demos without a real PDF OCR step
        raw_text = "\n".join(
            part
            for part in [
                f"Invoice Number: {payload.invoice_number}" if payload.invoice_number else None,
                f"Vendor: {payload.vendor_name}" if payload.vendor_name else None,
                f"Amount: {payload.amount}" if payload.amount is not None else None,
                f"Currency: {payload.currency}" if payload.currency else None,
                f"Invoice Date: {payload.invoice_date}" if payload.invoice_date else None,
                payload.description,
            ]
            if part
        )

    invoice = _latest_invoice(db, transaction_id)
    if invoice is None:
        invoice = Invoice(
            transaction_id=transaction_id,
            raw_ocr_text=raw_text,
            ocr_confidence=payload.ocr_confidence,
            extraction_status=EXTRACTION_STATUS_PENDING,
        )
        db.add(invoice)
    else:
        invoice.raw_ocr_text = raw_text
        invoice.ocr_confidence = payload.ocr_confidence
        invoice.extraction_error = None
        invoice.extraction_status = EXTRACTION_STATUS_PENDING

    db.commit()
    db.refresh(invoice)

    extraction = None

    # Structured fields take precedence (portfolio / demo path without Gemini OCR)
    if has_structured:
        invoice.invoice_number = payload.invoice_number
        invoice.vendor_name = payload.vendor_name
        invoice.invoice_date = payload.invoice_date
        invoice.due_date = payload.due_date
        invoice.amount = payload.amount
        invoice.currency = payload.currency.upper() if payload.currency else None
        invoice.description = payload.description
        invoice.extraction_status = EXTRACTION_STATUS_EXTRACTED
        invoice.extraction_error = None
        db.commit()
        db.refresh(invoice)
    elif payload.run_extraction and raw_text:
        try:
            extraction = extract_invoice(raw_text)
            apply_extraction(invoice, extraction)
            db.commit()
            db.refresh(invoice)
        except Exception as exc:
            invoice.extraction_status = "FAILED"
            invoice.extraction_error = str(exc)[:2000]
            db.commit()
            db.refresh(invoice)

    return InvoiceUploadResponse(
        invoice=_invoice_response(invoice),
        extraction=extraction,
    )


@router.post(
    "/{transaction_id}/invoice/verify",
    response_model=InvoiceVerificationResponse,
)
def verify_transaction_invoice(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    """
    Run Agent 2 for this transaction.

    With invoice → field comparison + verification.
    Without invoice → NOT_PROVIDED (does not fail).
    """
    transaction = db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    try:
        row = run_verification_for_transaction(db, transaction_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return InvoiceVerificationResponse.model_validate(row)


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
):
    db_transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id)
        .first()
    )
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    update_data = payload.model_dump(exclude_unset=True)
    company_id = update_data.get("company_id", db_transaction.company_id)
    vendor_id = update_data.get("vendor_id", db_transaction.vendor_id)
    category_id = update_data.get("category_id", db_transaction.category_id)

    if vendor_id is None or category_id is None:
        raise HTTPException(
            status_code=400,
            detail="vendor_id and category_id are required",
        )

    _validate_refs(
        db,
        company_id=company_id,
        vendor_id=vendor_id,
        category_id=category_id,
    )

    if "currency" in update_data and update_data["currency"]:
        update_data["currency"] = update_data["currency"].upper()

    for field, value in update_data.items():
        setattr(db_transaction, field, value)

    db.commit()

    txn = (
        db.query(Transaction)
        .options(
            joinedload(Transaction.company),
            joinedload(Transaction.vendor),
            joinedload(Transaction.category),
        )
        .filter(Transaction.id == transaction_id)
        .one()
    )
    return _to_response(txn)


# NOTE: ceil is imported at top of module
