"""make person outreach pattern inferred boolean

Revision ID: 30d3155efc9e
Revises: 1ee7ff0b9bc9
Create Date: 2026-09-05 17:02:44.669057

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30d3155efc9e'
down_revision: Union[str, Sequence[str], None] = '1ee7ff0b9bc9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "person_email_observations",
        "pattern_inferred",
        existing_type=sa.String(length=100),
        type_=sa.Boolean(),
        existing_nullable=True,
        postgresql_using=(
            "CASE "
            "WHEN pattern_inferred IS NULL THEN NULL "
            "WHEN lower(pattern_inferred) IN "
            "('true', 't', '1', 'yes', 'y') THEN TRUE "
            "ELSE FALSE "
            "END"
        ),
    )


def downgrade() -> None:
    op.alter_column(
        "person_email_observations",
        "pattern_inferred",
        existing_type=sa.Boolean(),
        type_=sa.String(length=100),
        existing_nullable=True,
        postgresql_using=(
            "CASE "
            "WHEN pattern_inferred IS NULL THEN NULL "
            "WHEN pattern_inferred THEN 'true' "
            "ELSE 'false' "
            "END"
        ),
    )
