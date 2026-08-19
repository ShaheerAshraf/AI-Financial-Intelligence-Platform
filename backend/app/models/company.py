from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    users = relationship(
        "User",
        back_populates="company",
        cascade="all, delete-orphan",
    )

    vendors = relationship(
        "Vendor",
        back_populates="company",
        cascade="all, delete-orphan",
    )

    categories = relationship(
        "Category",
        back_populates="company",
        cascade="all, delete-orphan",
    )

    transactions = relationship(
        "Transaction",
        back_populates="company",
        cascade="all, delete-orphan",
    )