from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.notification_preference import (
    NotificationPreferenceRepository,
)


@dataclass(slots=True, frozen=True)
class NotificationPreference:
    enabled: bool


class NotificationPreferenceService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get(
        self,
        *,
        user_id: int,
    ) -> NotificationPreference:
        async with self._session_factory() as session:
            repository = NotificationPreferenceRepository(session)
            preference = await repository.get_or_create(user_id)

            await session.commit()

            return NotificationPreference(
                enabled=preference.vip_journey_enabled,
            )

    async def is_enabled(
        self,
        *,
        user_id: int,
    ) -> bool:
        preference = await self.get(user_id=user_id)
        return preference.enabled

    async def set_enabled(
        self,
        *,
        user_id: int,
        enabled: bool,
    ) -> NotificationPreference:
        async with self._session_factory() as session:
            repository = NotificationPreferenceRepository(session)

            preference = await repository.set_enabled(
                user_id=user_id,
                enabled=enabled,
            )

            await session.commit()

            return NotificationPreference(
                enabled=preference.vip_journey_enabled,
            )

    async def toggle(
        self,
        *,
        user_id: int,
    ) -> NotificationPreference:
        current = await self.get(user_id=user_id)

        return await self.set_enabled(
            user_id=user_id,
            enabled=not current.enabled,
        )
