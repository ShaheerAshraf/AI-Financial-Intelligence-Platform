from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class InvoiceExtraction(BaseModel):
    """Structured fields extracted from raw OCR invoice text."""

    invoice_number: str | None = None
    vendor_name: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    amount: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    description: str | None = None
