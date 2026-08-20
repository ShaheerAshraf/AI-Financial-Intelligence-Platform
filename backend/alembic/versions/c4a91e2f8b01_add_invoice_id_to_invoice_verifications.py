"""add invoice_id to invoice_verifications

Revision ID: c4a91e2f8b01
Revises: b18d74f1dd04
Create Date: 2026-08-20 04:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4a91e2f8b01"
down_revision: Union[str, Sequence[str], None] = "b18d74f1dd04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Prior rows lack invoice linkage; safe to clear before adding NOT NULL FK.
    op.execute("DELETE FROM invoice_verifications")

    op.add_column(
        "invoice_verifications",
        sa.Column("invoice_id", sa.Integer(), nullable=False),
    )
    op.create_foreign_key(
        "fk_invoice_verifications_invoice_id",
        "invoice_verifications",
        "invoices",
        ["invoice_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_invoice_verifications_invoice_id"),
        "invoice_verifications",
        ["invoice_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_invoice_verifications_invoice_agent",
        "invoice_verifications",
        ["invoice_id", "agent_version"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_invoice_verifications_invoice_agent",
        "invoice_verifications",
        type_="unique",
    )
    op.drop_index(
        op.f("ix_invoice_verifications_invoice_id"),
        table_name="invoice_verifications",
    )
    op.drop_constraint(
        "fk_invoice_verifications_invoice_id",
        "invoice_verifications",
        type_="foreignkey",
    )
    op.drop_column("invoice_verifications", "invoice_id")
