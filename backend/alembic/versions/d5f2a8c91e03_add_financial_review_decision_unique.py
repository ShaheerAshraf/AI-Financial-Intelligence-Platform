"""add financial review decision and unique constraint

Revision ID: d5f2a8c91e03
Revises: c4a91e2f8b01
Create Date: 2026-08-20 04:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5f2a8c91e03"
down_revision: Union[str, Sequence[str], None] = "c4a91e2f8b01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "financial_reviews",
        sa.Column("decision", sa.String(length=30), nullable=False, server_default="MANUAL_REVIEW"),
    )
    op.alter_column("financial_reviews", "decision", server_default=None)
    op.create_index(
        op.f("ix_financial_reviews_decision"),
        "financial_reviews",
        ["decision"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_financial_reviews_transaction_agent",
        "financial_reviews",
        ["transaction_id", "agent_version"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_financial_reviews_transaction_agent",
        "financial_reviews",
        type_="unique",
    )
    op.drop_index(op.f("ix_financial_reviews_decision"), table_name="financial_reviews")
    op.drop_column("financial_reviews", "decision")
