"""add human review workflow fields to financial_reviews

Revision ID: e8a3b2c1d004
Revises: d5f2a8c91e03
Create Date: 2026-08-20 05:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8a3b2c1d004"
down_revision: Union[str, Sequence[str], None] = "d5f2a8c91e03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "financial_reviews",
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default="PENDING"),
    )
    op.add_column(
        "financial_reviews",
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "financial_reviews",
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "financial_reviews",
        sa.Column("review_comment", sa.Text(), nullable=True),
    )
    op.alter_column("financial_reviews", "review_status", server_default=None)
    op.create_index(
        op.f("ix_financial_reviews_review_status"),
        "financial_reviews",
        ["review_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_financial_reviews_review_status"), table_name="financial_reviews")
    op.drop_column("financial_reviews", "review_comment")
    op.drop_column("financial_reviews", "reviewed_at")
    op.drop_column("financial_reviews", "reviewed_by")
    op.drop_column("financial_reviews", "review_status")
