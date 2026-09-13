"""add free vs vip and compare settings

Revision ID: 76564da9ae59
Revises: 6f2ad5a70c61
Create Date: 2026-09-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "76564da9ae59"
down_revision: str | None = "6f2ad5a70c61"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "vip_menu_settings",
        sa.Column(
            "free_vs_vip_heading",
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.add_column(
        "vip_menu_settings",
        sa.Column(
            "free_vs_vip_info",
            sa.String(length=4000),
            nullable=True,
        ),
    )
    op.add_column(
        "vip_menu_settings",
        sa.Column(
            "free_vs_vip_promo_code",
            sa.String(length=128),
            nullable=True,
        ),
    )
    op.add_column(
        "vip_menu_settings",
        sa.Column(
            "free_vs_vip_support_username",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.add_column(
        "vip_menu_settings",
        sa.Column(
            "compare_heading",
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.add_column(
        "vip_menu_settings",
        sa.Column(
            "compare_intro",
            sa.String(length=4000),
            nullable=True,
        ),
    )

    op.add_column(
        "vip_categories",
        sa.Column(
            "compare_info",
            sa.String(length=4000),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("vip_categories", "compare_info")

    op.drop_column("vip_menu_settings", "compare_intro")
    op.drop_column("vip_menu_settings", "compare_heading")
    op.drop_column(
        "vip_menu_settings",
        "free_vs_vip_support_username",
    )
    op.drop_column(
        "vip_menu_settings",
        "free_vs_vip_promo_code",
    )
    op.drop_column("vip_menu_settings", "free_vs_vip_info")
    op.drop_column("vip_menu_settings", "free_vs_vip_heading")
