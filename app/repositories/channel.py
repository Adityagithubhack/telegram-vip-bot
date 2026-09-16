from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.channel import Channel


class ChannelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_required_active(self) -> list[Channel]:
        result = await self._session.execute(
            select(Channel)
            .where(
                Channel.is_required.is_(True),
                Channel.is_active.is_(True),
            )
            .order_by(
                Channel.priority.asc(),
                Channel.id.asc(),
            )
        )
        return list(result.scalars().all())

    async def get_by_id(self, channel_id: int) -> Channel | None:
        return await self._session.get(Channel, channel_id)

    async def create(
        self,
        *,
        telegram_chat_id: int,
        title: str,
        username: str | None,
        invite_url: str | None,
    ) -> Channel:
        channel = Channel(
            telegram_chat_id=telegram_chat_id,
            title=title,
            username=username,
            invite_url=invite_url,
            is_required=True,
            is_active=True,
            priority=100,
        )
        self._session.add(channel)
        await self._session.flush()
        return channel

    async def update(
        self,
        channel: Channel,
        *,
        telegram_chat_id: int,
        title: str,
        username: str | None,
        invite_url: str | None,
    ) -> Channel:
        channel.telegram_chat_id = telegram_chat_id
        channel.title = title
        channel.username = username
        channel.invite_url = invite_url
        await self._session.flush()
        return channel
