"""add vip display name

Revision ID: 6f2ad5a70c61
Revises: 44d0d46638a4
Create Date: 2026-09-13
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "6f2ad5a70c61"
down_revision: str | Sequence[str] | None = "44d0d46638a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "vip_categories",
        sa.Column(
            "display_name",
            sa.String(length=128),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE vip_categories
        SET display_name = CASE
            WHEN code = 'standard' THEN 'Standard VIP'
            WHEN code = 'premium' THEN 'Premium VIP'
            WHEN code = 'elite' THEN 'Elite VIP'
            ELSE INITCAP(REPLACE(code, '_', ' ')) || ' VIP'
        END
        WHERE display_name IS NULL
        """
    )

    op.alter_column(
        "vip_categories",
        "display_name",
        existing_type=sa.String(length=128),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column(
        "vip_categories",
        "display_name",
    )
