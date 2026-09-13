from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db.base import Base


class VipMenuSettings(Base):
    __tablename__ = "vip_menu_settings"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    heading: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="WHICH VIP EXPERIENCE INTERESTS YOU MOST?",
    )

    description: Mapped[str | None] = mapped_column(
        String(4000),
        nullable=True,
    )

    footer_text: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Tap any option below 👇",
    )

    free_vs_vip_heading: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    free_vs_vip_info: Mapped[str | None] = mapped_column(
        String(4000),
        nullable=True,
    )
    free_vs_vip_promo_code: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    free_vs_vip_support_username: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    compare_heading: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    compare_intro: Mapped[str | None] = mapped_column(
        String(4000),
        nullable=True,
    )
    live_bets_heading: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    live_bets_info: Mapped[str | None] = mapped_column(
        String(4000),
        nullable=True,
    )
    pre_match_bets_heading: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    pre_match_bets_info: Mapped[str | None] = mapped_column(
        String(4000),
        nullable=True,
    )

    live_bets_media_file_id: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    live_bets_media_type: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    pre_match_bets_media_file_id: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    pre_match_bets_media_type: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
