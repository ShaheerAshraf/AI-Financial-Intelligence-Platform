from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.agents.invoice_agent import AGENT_VERSION as INVOICE_AGENT_VERSION
from app.agents.review_agent import AGENT_VERSION as REVIEW_AGENT_VERSION
from app.agents.transaction_agent import AGENT_VERSION as TRANSACTION_AGENT_VERSION
from app.models.anomaly_result import AnomalyResult
from app.models.financial_review import FinancialReview
from app.models.invoice import Invoice
from app.models.invoice_verification import InvoiceVerification
from app.models.transaction import Transaction
from app.models.transaction_analysis import TransactionAnalysis
from app.schemas.financial_review import (
    FieldComparisonItem,
    FinancialInvestigationResponse,
    InvestigationAnomaly,
    InvestigationFinancialReview,
    InvestigationInvoice,
    InvestigationInvoiceVerification,
    InvestigationTransaction,
    InvestigationTransactionAnalysis,
    ReviewListItem,
)
from app.services.invoice_comparison import compute_field_comparisons


def _verification_reason(verification: InvoiceVerification) -> str | None:
    if verification.mismatches:
        return "; ".join(verification.mismatches)
    return verification.summary


def _latest_anomaly(db: Session, transaction_id: int) -> AnomalyResult | None:
    return (
        db.query(AnomalyResult)
        .filter(AnomalyResult.transaction_id == transaction_id)
        .order_by(AnomalyResult.detected_at.desc())
        .first()
    )


def _latest_analysis(db: Session, transaction_id: int) -> TransactionAnalysis | None:
    return (
        db.query(TransactionAnalysis)
        .filter(
            TransactionAnalysis.transaction_id == transaction_id,
            TransactionAnalysis.agent_version == TRANSACTION_AGENT_VERSION,
        )
        .order_by(TransactionAnalysis.created_at.desc())
        .first()
    )


def _latest_verification(db: Session, transaction_id: int) -> InvoiceVerification | None:
    return (
        db.query(InvoiceVerification)
        .filter(
            InvoiceVerification.transaction_id == transaction_id,
            InvoiceVerification.agent_version == INVOICE_AGENT_VERSION,
        )
        .order_by(InvoiceVerification.created_at.desc())
        .first()
    )


def _latest_review(db: Session, transaction_id: int) -> FinancialReview | None:
    return (
        db.query(FinancialReview)
        .filter(
            FinancialReview.transaction_id == transaction_id,
            FinancialReview.agent_version == REVIEW_AGENT_VERSION,
        )
        .order_by(FinancialReview.created_at.desc())
        .first()
    )


def _invoice_for_verification(
    db: Session,
    verification: InvoiceVerification | None,
    transaction_id: int,
) -> Invoice | None:
    if verification is not None and verification.invoice_id is not None:
        return db.get(Invoice, verification.invoice_id)
    return (
        db.query(Invoice)
        .filter(Invoice.transaction_id == transaction_id)
        .order_by(Invoice.id.desc())
        .first()
    )


def _field_comparisons_payload(
    verification: InvoiceVerification | None,
    transaction: Transaction,
    invoice: Invoice | None,
) -> list[FieldComparisonItem]:
    raw: list[dict] = []
    if verification and verification.field_comparisons:
        raw = list(verification.field_comparisons)
    elif invoice is not None:
        vendor_name = transaction.vendor.name if transaction.vendor else None
        raw = compute_field_comparisons(
            transaction_amount=transaction.amount,
            transaction_currency=transaction.currency,
            transaction_date=transaction.transaction_date,
            transaction_vendor_name=vendor_name,
            invoice_amount=invoice.amount,
            invoice_currency=invoice.currency,
            invoice_date=invoice.invoice_date,
            invoice_vendor_name=invoice.vendor_name,
        )

    items: list[FieldComparisonItem] = []
    for item in raw:
        items.append(
            FieldComparisonItem(
                field=item.get("field", ""),
                label=item.get("label", item.get("field", "")),
                transaction_value=str(item.get("transaction_value", "—")),
                invoice_value=str(item.get("invoice_value", "—")),
                status=item.get("status", "MISSING"),
                detail=item.get("detail"),
            )
        )
    return items


def _amount_difference(
    transaction: Transaction,
    invoice: Invoice | None,
) -> Decimal | None:
    if invoice is None or invoice.amount is None:
        return None
    return abs(Decimal(transaction.amount) - Decimal(invoice.amount))


def build_investigation(
    db: Session,
    transaction: Transaction,
) -> FinancialInvestigationResponse:
    if transaction.company is None or transaction.vendor is None or transaction.category is None:
        transaction = (
            db.query(Transaction)
            .options(
                joinedload(Transaction.company),
                joinedload(Transaction.vendor),
                joinedload(Transaction.category),
            )
            .filter(Transaction.id == transaction.id)
            .one()
        )

    anomaly = _latest_anomaly(db, transaction.id)
    analysis = _latest_analysis(db, transaction.id)
    verification = _latest_verification(db, transaction.id)
    review = _latest_review(db, transaction.id)
    invoice = _invoice_for_verification(db, verification, transaction.id)
    field_comparisons = _field_comparisons_payload(verification, transaction, invoice)

    invoice_verification_payload = None
    if verification:
        invoice_verification_payload = InvestigationInvoiceVerification(
            status=verification.match_status,
            reason=_verification_reason(verification),
            summary=verification.summary,
            mismatches=verification.mismatches or [],
            field_comparisons=field_comparisons,
            invoice_id=verification.invoice_id,
            recommendation=verification.recommendation,
            amount_difference=_amount_difference(transaction, invoice),
        )
    elif invoice is None:
        invoice_verification_payload = InvestigationInvoiceVerification(
            status="NOT_PROVIDED",
            reason="No invoice attached to this transaction",
            summary="Invoice status: NOT PROVIDED",
            mismatches=[],
            field_comparisons=[],
            invoice_id=None,
            recommendation="Attach invoice data if verification is required",
            amount_difference=None,
        )
    elif invoice is not None:
        invoice_verification_payload = InvestigationInvoiceVerification(
            status="PENDING",
            reason="Invoice attached but not verified yet",
            summary="Click Verify Invoice to compare against the transaction",
            mismatches=[],
            field_comparisons=field_comparisons,
            invoice_id=invoice.id,
            recommendation="Run invoice verification",
            amount_difference=_amount_difference(transaction, invoice),
        )

    return FinancialInvestigationResponse(
        transaction=InvestigationTransaction(
            id=transaction.id,
            amount=transaction.amount,
            vendor_id=transaction.vendor_id,
            category_id=transaction.category_id,
            date=transaction.transaction_date,
            currency=transaction.currency,
            description=transaction.description,
            analysis_status=getattr(transaction, "analysis_status", "NEW"),
            vendor_name=transaction.vendor.name if transaction.vendor else None,
            category_name=transaction.category.name if transaction.category else None,
            company_name=transaction.company.name if transaction.company else None,
        ),
        anomaly=(
            InvestigationAnomaly(
                score=anomaly.anomaly_score,
                status=anomaly.status,
                reason=anomaly.reason,
                model_version=anomaly.model_version,
            )
            if anomaly
            else None
        ),
        transaction_analysis=(
            InvestigationTransactionAnalysis(
                risk_level=analysis.risk_level,
                summary=analysis.summary,
                recommendation=analysis.recommendation,
                findings=analysis.findings or [],
            )
            if analysis
            else None
        ),
        invoice=(
            InvestigationInvoice(
                id=invoice.id,
                invoice_number=invoice.invoice_number,
                amount=invoice.amount,
                vendor_name=invoice.vendor_name,
                invoice_date=invoice.invoice_date,
                currency=invoice.currency,
                extraction_status=invoice.extraction_status,
            )
            if invoice
            else None
        ),
        invoice_verification=invoice_verification_payload,
        financial_review=(
            InvestigationFinancialReview(
                risk_level=review.final_risk_level,
                decision=review.decision,
                summary=review.summary,
                recommendation=review.recommendation,
                findings=review.findings or [],
                review_status=review.review_status,
                reviewed_by=review.reviewed_by,
                reviewed_at=review.reviewed_at,
                review_comment=review.review_comment,
            )
            if review
            else None
        ),
    )


def build_review_list_item(
    db: Session,
    review: FinancialReview,
    transaction: Transaction,
) -> ReviewListItem:
    anomaly = _latest_anomaly(db, transaction.id)
    verification = _latest_verification(db, transaction.id)

    return ReviewListItem(
        transaction_id=transaction.id,
        amount=transaction.amount,
        vendor_name=transaction.vendor.name if transaction.vendor else None,
        category_name=transaction.category.name if transaction.category else None,
        anomaly_status=anomaly.status if anomaly else None,
        invoice_status=verification.match_status if verification else "NOT_PROVIDED",
        final_risk=review.final_risk_level,
        decision=review.decision,
        review_status=review.review_status,
    )
