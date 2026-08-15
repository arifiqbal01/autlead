"""add company address category

Revision ID: cb1a2d4f7e83
Revises: 7c9f5f2e9a61
Create Date: 2026-08-14 15:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cb1a2d4f7e83"
down_revision: str | Sequence[str] | None = "7c9f5f2e9a61"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("companies", sa.Column("address", sa.String(length=500), nullable=True))
    op.add_column("companies", sa.Column("category", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("companies", "category")
    op.drop_column("companies", "address")
