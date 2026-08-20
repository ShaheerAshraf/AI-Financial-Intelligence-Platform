from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    vendor_id: Mapped[int | None] = mapped_column(
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="EUR",
    )

    transaction_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    analysis_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="NEW",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    company = relationship(
        "Company",
        back_populates="transactions",
    )

    vendor = relationship(
        "Vendor",
        back_populates="transactions",
    )

    category = relationship(
        "Category",
        back_populates="transactions",
    )

    anomaly_results = relationship(
        "AnomalyResult",
        back_populates="transaction",
        cascade="all, delete-orphan",
    )

    transaction_analyses = relationship(
        "TransactionAnalysis",
        back_populates="transaction",
        cascade="all, delete-orphan",
    )

    invoice_verifications = relationship(
        "InvoiceVerification",
        back_populates="transaction",
        cascade="all, delete-orphan",
    )

    financial_reviews = relationship(
        "FinancialReview",
        back_populates="transaction",
        cascade="all, delete-orphan",
    )

    invoices = relationship(
        "Invoice",
        back_populates="transaction",
        cascade="all, delete-orphan",
    )
