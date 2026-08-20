from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    company_id: int
    vendor_id: int
    category_id: int
    amount: Decimal = Field(gt=0)
    currency: str = "EUR"
    description: str | None = None
    transaction_date: date


class TransactionUpdate(BaseModel):
    company_id: int | None = None
    vendor_id: int | None = None
    category_id: int | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = None
    description: str | None = None
    transaction_date: date | None = None


class TransactionResponse(BaseModel):
    id: int
    company_id: int
    vendor_id: int | None
    category_id: int | None
    amount: Decimal
    currency: str
    description: str | None
    transaction_date: date
    analysis_status: str = "NEW"
    company_name: str | None = None
    vendor_name: str | None = None
    category_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedTransactionsResponse(BaseModel):
    items: list[TransactionResponse]
    page: int
    limit: int
    total: int
    pages: int


class TransactionImportRowError(BaseModel):
    row: int
    field: str | None = None
    message: str
    company: str | None = None
    vendor: str | None = None
    category: str | None = None


class TransactionImportResponse(BaseModel):
    imported: int
    failed: int
    total_rows: int
    created_ids: list[int] = Field(default_factory=list)
    errors: list[TransactionImportRowError] = Field(default_factory=list)
