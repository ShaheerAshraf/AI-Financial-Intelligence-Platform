"""add transaction analysis_status

Revision ID: f9b1c2d3e004
Revises: e8a3b2c1d004
Create Date: 2026-08-20 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f9b1c2d3e004"
down_revision: Union[str, Sequence[str], None] = "e8a3b2c1d004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column(
            "analysis_status",
            sa.String(length=20),
            nullable=False,
            server_default="NEW",
        ),
    )
    # Existing rows that already have a financial review were analyzed.
    op.execute(
        """
        UPDATE transactions
        SET analysis_status = 'ANALYZED'
        WHERE id IN (SELECT DISTINCT transaction_id FROM financial_reviews)
           OR id IN (SELECT DISTINCT transaction_id FROM transaction_analyses)
        """
    )
    op.alter_column("transactions", "analysis_status", server_default=None)
    op.create_index(
        op.f("ix_transactions_analysis_status"),
        "transactions",
        ["analysis_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_transactions_analysis_status"), table_name="transactions")
    op.drop_column("transactions", "analysis_status")
