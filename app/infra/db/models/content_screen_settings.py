from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func

from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db.base import Base


class ContentScreenSettings(Base):

    __tablename__ = "content_screen_settings"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    screen_key: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )

    heading: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    footer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    media_file_id: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    media_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    registration_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )

    promo_code: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    support_username: Mapped[str | None] = mapped_column(
        String(255),
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
