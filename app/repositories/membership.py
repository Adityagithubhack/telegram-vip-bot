from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.channel_membership import ChannelMembership
from app.infra.db.models.membership_check import MembershipCheck


class MembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest(
        self,
        *,
        user_id: int,
        channel_id: int,
    ) -> ChannelMembership | None:
        result = await self._session.execute(
            select(ChannelMembership).where(
                ChannelMembership.user_id == user_id,
                ChannelMembership.channel_id == channel_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_latest(
        self,
        *,
        user_id: int,
        channel_id: int,
        telegram_status: str,
        is_satisfied: bool,
        checked_at: datetime,
        expires_at: datetime | None,
    ) -> ChannelMembership:
        statement = (
            insert(ChannelMembership)
            .values(
                user_id=user_id,
                channel_id=channel_id,
                telegram_status=telegram_status,
                is_satisfied=is_satisfied,
                checked_at=checked_at,
                expires_at=expires_at,
            )
            .on_conflict_do_update(
                constraint="uq_channel_memberships_user_channel",
                set_={
                    "telegram_status": telegram_status,
                    "is_satisfied": is_satisfied,
                    "checked_at": checked_at,
                    "expires_at": expires_at,
                },
            )
            .returning(ChannelMembership)
        )

        result = await self._session.execute(statement)
        return result.scalar_one()

    async def add_check(
        self,
        *,
        user_id: int,
        channel_id: int,
        telegram_status: str | None,
        is_satisfied: bool,
        source: str,
        error: str | None,
        latency_ms: int | None,
        checked_at: datetime,
    ) -> MembershipCheck:
        check = MembershipCheck(
            user_id=user_id,
            channel_id=channel_id,
            telegram_status=telegram_status,
            is_satisfied=is_satisfied,
            source=source,
            error=error,
            latency_ms=latency_ms,
            checked_at=checked_at,
        )

        self._session.add(check)
        await self._session.flush()

        return check
