from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.db.models.channel import Channel
from app.repositories.channel import ChannelRepository


class ChannelSettingsService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get_required_channel(self) -> Channel | None:
        async with self._session_factory() as session:
            repository = ChannelRepository(session)
            channels = await repository.get_required_active()
            return channels[0] if channels else None

    async def update_required_channel(
        self,
        *,
        channel_id: int,
        telegram_chat_id: int,
        title: str,
        username: str | None,
        invite_url: str | None,
    ) -> Channel | None:
        async with self._session_factory() as session:
            repository = ChannelRepository(session)
            channel = await repository.get_by_id(channel_id)

            if channel is None:
                return None

            channel = await repository.update(
                channel,
                telegram_chat_id=telegram_chat_id,
                title=title,
                username=username,
                invite_url=invite_url,
            )

            await session.commit()
            return channel
