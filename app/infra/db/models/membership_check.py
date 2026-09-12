from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db.base import Base


class MembershipCheck(Base):
    __tablename__ = "membership_checks"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    telegram_status: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    is_satisfied: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(32),
        default="telegram_api",
        server_default="telegram_api",
        nullable=False,
    )

    error: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
