from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class InvestigationTransaction(BaseModel):
    id: int
    amount: Decimal
    vendor_id: int | None
    category_id: int | None
    date: date
    currency: str = "EUR"
    description: str | None = None
    analysis_status: str = "NEW"
    vendor_name: str | None = None
    category_name: str | None = None
    company_name: str | None = None


class InvestigationAnomaly(BaseModel):
    score: float
    status: str
    reason: str | None = None
    model_version: str | None = None


class InvestigationTransactionAnalysis(BaseModel):
    risk_level: str
    summary: str
    recommendation: str
    findings: list[str] = Field(default_factory=list)


class InvestigationInvoice(BaseModel):
    id: int | None = None
    invoice_number: str | None = None
    amount: Decimal | None = None
    vendor_name: str | None = None
    invoice_date: date | None = None
    currency: str | None = None
    extraction_status: str | None = None


class FieldComparisonItem(BaseModel):
    field: str
    label: str
    transaction_value: str
    invoice_value: str
    status: str
    detail: str | None = None


class InvestigationInvoiceVerification(BaseModel):
    status: str
    reason: str | None = None
    summary: str | None = None
    mismatches: list[str] = Field(default_factory=list)
    field_comparisons: list[FieldComparisonItem] = Field(default_factory=list)
    invoice_id: int | None = None
    recommendation: str | None = None
    amount_difference: Decimal | None = None


class InvestigationFinancialReview(BaseModel):
    risk_level: str
    decision: str
    summary: str
    recommendation: str
    findings: list[str] = Field(default_factory=list)
    review_status: str = "PENDING"
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_comment: str | None = None


class FinancialInvestigationResponse(BaseModel):
    transaction: InvestigationTransaction
    anomaly: InvestigationAnomaly | None = None
    transaction_analysis: InvestigationTransactionAnalysis | None = None
    invoice: InvestigationInvoice | None = None
    invoice_verification: InvestigationInvoiceVerification | None = None
    financial_review: InvestigationFinancialReview | None = None


class ReviewListItem(BaseModel):
    transaction_id: int
    amount: Decimal
    vendor_name: str | None = None
    category_name: str | None = None
    anomaly_status: str | None = None
    invoice_status: str | None = None
    final_risk: str | None = None
    decision: str | None = None
    review_status: str | None = None


class PaginatedReviewsResponse(BaseModel):
    items: list[ReviewListItem]
    page: int
    limit: int
    total: int
    pages: int


class DashboardSummaryResponse(BaseModel):
    total_transactions: int
    total_anomalies: int
    high_risk_transactions: int
    pending_reviews: int
    invoice_mismatches: int
    manual_reviews: int


class AnomalyTrendPoint(BaseModel):
    date: date
    count: int


class RiskDistributionItem(BaseModel):
    status: str
    count: int


class RecentHighRiskItem(BaseModel):
    transaction_id: int
    amount: Decimal
    vendor_id: int | None
    category_id: int | None
    vendor_name: str | None = None
    anomaly_score: float
    status: str
    transaction_date: date


class RecentReviewItem(BaseModel):
    transaction_id: int
    amount: Decimal
    final_risk: str
    decision: str
    review_status: str
    created_at: datetime


class DashboardOverviewResponse(BaseModel):
    summary: DashboardSummaryResponse
    anomaly_trend: list[AnomalyTrendPoint]
    risk_distribution: list[RiskDistributionItem]
    recent_high_risk: list[RecentHighRiskItem]
    recent_reviews: list[RecentReviewItem]


class HumanReviewDecision(BaseModel):
    decision: Literal["APPROVED", "REJECTED", "ESCALATED"]
    reviewed_by: str = Field(min_length=1)
    comment: str = Field(min_length=1)


class AnomalyListItem(BaseModel):
    transaction_id: int
    amount: Decimal
    vendor_id: int | None
    category_id: int | None
    vendor_name: str | None = None
    category_name: str | None = None
    anomaly_score: float
    status: str
    reason: str | None = None
    transaction_date: date


class InvoiceListItem(BaseModel):
    id: int
    transaction_id: int
    invoice_number: str | None
    vendor_name: str | None
    amount: Decimal | None
    currency: str | None
    invoice_date: date | None
    extraction_status: str
    match_status: str | None = None


class PaginatedAnomaliesResponse(BaseModel):
    items: list[AnomalyListItem]
    page: int
    limit: int
    total: int
    pages: int


class PaginatedInvoicesResponse(BaseModel):
    items: list[InvoiceListItem]
    page: int
    limit: int
    total: int
    pages: int
