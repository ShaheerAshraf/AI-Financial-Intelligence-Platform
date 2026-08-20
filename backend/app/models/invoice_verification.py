from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InvoiceVerification(Base):
    __tablename__ = "invoice_verifications"
    __table_args__ = (
        UniqueConstraint(
            "invoice_id",
            "agent_version",
            name="uq_invoice_verifications_invoice_agent",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    match_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    mismatches: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    field_comparisons: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    evidence: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    recommendation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    agent_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    invoice = relationship(
        "Invoice",
        back_populates="invoice_verifications",
    )

    transaction = relationship(
        "Transaction",
        back_populates="invoice_verifications",
    )
