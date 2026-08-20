"""nullable invoice_id and field_comparisons on invoice_verifications

Revision ID: h1d3e4f50607
Revises: g0c2d3e4f005
Create Date: 2026-08-20 23:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "h1d3e4f50607"
down_revision: Union[str, Sequence[str], None] = "g0c2d3e4f005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "invoice_verifications",
        "invoice_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.add_column(
        "invoice_verifications",
        sa.Column(
            "field_comparisons",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )
    op.alter_column(
        "invoice_verifications",
        "field_comparisons",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("invoice_verifications", "field_comparisons")
    # Only safe if no NULL invoice_id rows remain
    op.execute(
        "DELETE FROM invoice_verifications WHERE invoice_id IS NULL"
    )
    op.alter_column(
        "invoice_verifications",
        "invoice_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
