from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.db.models.daily_pick import DailyPick
from app.repositories.daily_pick import DailyPickRepository


class DailyPickService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def create_pick(
        self,
        *,
        sport: str,
        event_title: str,
        selection: str,
        confidence: int,
        odds: float | None,
        analysis: str | None,
    ) -> DailyPick:
        if not 0 <= confidence <= 100:
            raise ValueError("confidence must be between 0 and 100")

        async with self._session_factory() as session:
            repository = DailyPickRepository(session)

            pick = await repository.create(
                sport=sport,
                event_title=event_title,
                selection=selection,
                confidence=confidence,
                odds=odds,
                analysis=analysis,
            )

            await session.commit()

            return pick

    async def publish_pick(
        self,
        *,
        pick_id: int,
    ) -> DailyPick | None:
        async with self._session_factory() as session:
            repository = DailyPickRepository(session)

            pick = await repository.publish(
                pick_id=pick_id,
                published_at=datetime.now(UTC),
            )

            if pick is None:
                return None

            await session.commit()

            return pick

    async def list_published(self) -> list[DailyPick]:
        async with self._session_factory() as session:
            repository = DailyPickRepository(session)

            return await repository.list_published()
