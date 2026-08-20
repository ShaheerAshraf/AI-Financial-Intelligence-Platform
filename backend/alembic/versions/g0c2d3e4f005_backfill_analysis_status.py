"""backfill analysis_status for existing ml results

Revision ID: g0c2d3e4f005
Revises: f9b1c2d3e004
Create Date: 2026-08-20 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "g0c2d3e4f005"
down_revision: Union[str, Sequence[str], None] = "f9b1c2d3e004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rows that already have ML/agent outputs should not appear as NEW.
    op.execute(
        """
        UPDATE transactions
        SET analysis_status = 'ANALYZED'
        WHERE analysis_status = 'NEW'
          AND (
            id IN (SELECT DISTINCT transaction_id FROM anomaly_results)
            OR id IN (SELECT DISTINCT transaction_id FROM transaction_analyses)
            OR id IN (SELECT DISTINCT transaction_id FROM financial_reviews)
          )
        """
    )


def downgrade() -> None:
    # Irreversible data backfill — no-op.
    pass
