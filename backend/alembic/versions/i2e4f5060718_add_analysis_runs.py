"""add analysis_runs and ANALYSIS_FAILED status

Revision ID: i2e4f5060718
Revises: h1d3e4f50607
Create Date: 2026-08-21 00:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "i2e4f5060718"
down_revision: Union[str, Sequence[str], None] = "h1d3e4f50607"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("batch_size", sa.Integer(), nullable=False),
        sa.Column("total_transactions", sa.Integer(), nullable=False),
        sa.Column("successful", sa.Integer(), nullable=False),
        sa.Column("failed", sa.Integer(), nullable=False),
        sa.Column("high_risk", sa.Integer(), nullable=False),
        sa.Column("medium_risk", sa.Integer(), nullable=False),
        sa.Column("low_risk", sa.Integer(), nullable=False),
        sa.Column("remaining_new_after", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analysis_runs_started_at"), "analysis_runs", ["started_at"])
    op.create_index(op.f("ix_analysis_runs_status"), "analysis_runs", ["status"])

    op.create_table(
        "analysis_run_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("workflow_status", sa.String(length=30), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_analysis_run_items_run_id"), "analysis_run_items", ["run_id"]
    )
    op.create_index(
        op.f("ix_analysis_run_items_transaction_id"),
        "analysis_run_items",
        ["transaction_id"],
    )
    op.create_index(
        op.f("ix_analysis_run_items_status"), "analysis_run_items", ["status"]
    )

    # Normalize legacy failure status
    op.execute(
        """
        UPDATE transactions
        SET analysis_status = 'ANALYSIS_FAILED'
        WHERE analysis_status = 'FAILED'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE transactions
        SET analysis_status = 'FAILED'
        WHERE analysis_status = 'ANALYSIS_FAILED'
        """
    )
    op.drop_index(op.f("ix_analysis_run_items_status"), table_name="analysis_run_items")
    op.drop_index(
        op.f("ix_analysis_run_items_transaction_id"), table_name="analysis_run_items"
    )
    op.drop_index(op.f("ix_analysis_run_items_run_id"), table_name="analysis_run_items")
    op.drop_table("analysis_run_items")
    op.drop_index(op.f("ix_analysis_runs_status"), table_name="analysis_runs")
    op.drop_index(op.f("ix_analysis_runs_started_at"), table_name="analysis_runs")
    op.drop_table("analysis_runs")
