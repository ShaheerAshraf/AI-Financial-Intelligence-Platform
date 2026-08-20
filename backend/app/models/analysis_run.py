from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="NEW",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="RUNNING",
        index=True,
    )

    batch_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    total_transactions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    successful: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    failed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    high_risk: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    medium_risk: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    low_risk: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    remaining_new_after: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    items = relationship(
        "AnalysisRunItem",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AnalysisRunItem.id",
    )


class AnalysisRunItem(Base):
    __tablename__ = "analysis_run_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        index=True,
    )

    workflow_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    risk_level: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    run = relationship("AnalysisRun", back_populates="items")
