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
