from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.invoice import InvoiceExtraction


class InvoiceCreate(BaseModel):
    """Create invoice via global /api/invoices/ endpoint."""

    transaction_id: int
    raw_ocr_text: str = Field(min_length=1)
    ocr_confidence: float | None = Field(default=None, ge=0, le=1)
    run_extraction: bool = True


class TransactionInvoiceCreate(BaseModel):
    """
    Attach invoice data to a transaction.

    Provide raw_ocr_text for OCR extraction, and/or structured fields
    for portfolio demos without calling Gemini extraction.
    """

    raw_ocr_text: str | None = Field(default=None, min_length=1)
    ocr_confidence: float | None = Field(default=None, ge=0, le=1)
    run_extraction: bool = True
    invoice_number: str | None = None
    vendor_name: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    description: str | None = None


class InvoiceResponse(BaseModel):
    id: int
    transaction_id: int
    invoice_number: str | None
    vendor_name: str | None
    invoice_date: date | None
    due_date: date | None
    amount: Decimal | None
    currency: str | None
    description: str | None
    ocr_confidence: float | None
    extraction_status: str
    extraction_error: str | None
    created_at: datetime
    raw_ocr_text: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InvoiceUploadResponse(BaseModel):
    invoice: InvoiceResponse
    extraction: InvoiceExtraction | None = None


class InvoiceVerificationResponse(BaseModel):
    id: int
    transaction_id: int
    invoice_id: int | None
    match_status: str
    summary: str
    mismatches: list[str] = Field(default_factory=list)
    field_comparisons: list[dict] = Field(default_factory=list)
    recommendation: str
    agent_version: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
