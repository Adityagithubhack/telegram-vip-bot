from datetime import datetime

from sqlalchemy import Boolean, DateTime, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db.base import Base


class DailyPick(Base):
    __tablename__ = "daily_picks"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    sport: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    event_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    selection: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    confidence: Mapped[int] = mapped_column(
        nullable=False,
    )

    odds: Mapped[float | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )

    analysis: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_published: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
