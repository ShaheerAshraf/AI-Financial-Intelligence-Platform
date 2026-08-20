from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TransactionAnalysis(Base):
    __tablename__ = "transaction_analyses"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    findings: Mapped[list] = mapped_column(
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

    transaction = relationship(
        "Transaction",
        back_populates="transaction_analyses",
    )
