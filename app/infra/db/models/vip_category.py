from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db.base import Base


class VipCategory(Base):
    __tablename__ = "vip_categories"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )

    name_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )


    description_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    vip_info: Mapped[str | None] = mapped_column(
        String(4000),
        nullable=True,
    )

    compare_info: Mapped[str | None] = mapped_column(
        String(4000),
        nullable=True,
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=100,
        server_default="100",
        nullable=False,
    )

    registration_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    promo_code: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    support_username: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    media_file_id: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    media_type: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
