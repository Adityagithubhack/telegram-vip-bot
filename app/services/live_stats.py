from dataclasses import dataclass

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.db.models.channel_membership import ChannelMembership
from app.infra.db.models.user import User
from app.infra.db.models.user_onboarding import UserOnboarding


@dataclass(slots=True, frozen=True)
class LiveStats:
    bot_members: int
    channel_joins: int
    vip_members: int


class LiveStatsService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get_stats(self) -> LiveStats:
        async with self._session_factory() as session:
            bot_members_result = await session.execute(
                select(func.count(User.id)).where(
                    User.is_active.is_(True),
                    User.is_bot.is_(False),
                )
            )

            channel_joins_result = await session.execute(
                select(
                    func.count(distinct(ChannelMembership.user_id))
                ).where(
                    ChannelMembership.is_satisfied.is_(True)
                )
            )

            vip_members_result = await session.execute(
                select(func.count(UserOnboarding.user_id)).where(
                    UserOnboarding.vip_access_granted_at.is_not(None)
                )
            )

            return LiveStats(
                bot_members=int(bot_members_result.scalar_one()),
                channel_joins=int(channel_joins_result.scalar_one()),
                vip_members=int(vip_members_result.scalar_one()),
            )
