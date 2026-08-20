"""add invoice extraction status fields

Revision ID: b18d74f1dd04
Revises: e7efb2157693
Create Date: 2026-08-20 04:08:32.478684

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b18d74f1dd04"
down_revision: Union[str, Sequence[str], None] = "e7efb2157693"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column(
            "extraction_status",
            sa.String(length=20),
            nullable=False,
            server_default="PENDING",
        ),
    )
    op.add_column(
        "invoices",
        sa.Column("extraction_error", sa.Text(), nullable=True),
    )
    op.create_index(
        op.f("ix_invoices_extraction_status"),
        "invoices",
        ["extraction_status"],
        unique=False,
    )
    op.alter_column("invoices", "extraction_status", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_invoices_extraction_status"), table_name="invoices")
    op.drop_column("invoices", "extraction_error")
    op.drop_column("invoices", "extraction_status")
