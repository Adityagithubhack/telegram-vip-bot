from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.user_notification_preference import (
    UserNotificationPreference,
)


class NotificationPreferenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(
        self,
        user_id: int,
    ) -> UserNotificationPreference | None:
        result = await self._session.execute(
            select(UserNotificationPreference).where(
                UserNotificationPreference.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        user_id: int,
    ) -> UserNotificationPreference:
        preference = await self.get_by_user_id(user_id)

        if preference is not None:
            return preference

        preference = UserNotificationPreference(
            user_id=user_id,
            vip_journey_enabled=True,
        )
        self._session.add(preference)
        await self._session.flush()

        return preference

    async def set_enabled(
        self,
        *,
        user_id: int,
        enabled: bool,
    ) -> UserNotificationPreference:
        preference = await self.get_or_create(user_id)
        preference.vip_journey_enabled = enabled

        await self._session.flush()
        return preference
