from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.daily_pick import DailyPick


class DailyPickRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        sport: str,
        event_title: str,
        selection: str,
        confidence: int,
        odds: float | None,
        analysis: str | None,
    ) -> DailyPick:
        pick = DailyPick(
            sport=sport,
            event_title=event_title,
            selection=selection,
            confidence=confidence,
            odds=odds,
            analysis=analysis,
            is_published=False,
        )

        self._session.add(pick)
        await self._session.flush()

        return pick

    async def publish(
        self,
        *,
        pick_id: int,
        published_at: datetime,
    ) -> DailyPick | None:
        result = await self._session.execute(
            select(DailyPick).where(DailyPick.id == pick_id)
        )

        pick = result.scalar_one_or_none()

        if pick is None:
            return None

        pick.is_published = True
        pick.published_at = published_at

        await self._session.flush()

        return pick

    async def list_published(self) -> list[DailyPick]:
        result = await self._session.execute(
            select(DailyPick)
            .where(DailyPick.is_published.is_(True))
            .order_by(
                DailyPick.published_at.desc(),
                DailyPick.id.desc(),
            )
        )

        return list(result.scalars().all())

    async def get_by_id(
        self,
        pick_id: int,
    ) -> DailyPick | None:
        result = await self._session.execute(
            select(DailyPick).where(DailyPick.id == pick_id)
        )

        return result.scalar_one_or_none()
