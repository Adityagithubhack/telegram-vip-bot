from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.content_screen_settings import ContentScreenSettings


class ContentScreenSettingsRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_key(
        self,
        screen_key: str,
    ) -> ContentScreenSettings | None:
        result = await self._session.execute(
            select(ContentScreenSettings).where(
                ContentScreenSettings.screen_key == screen_key
            )
        )
        return result.scalar_one_or_none()

    async def update_content(
        self,
        *,
        screen_key: str,
        heading: str | None,
        body: str | None,
        footer: str | None,
        registration_url: str | None,
        promo_code: str | None,
        support_username: str | None,
    ) -> ContentScreenSettings | None:
        settings = await self.get_by_key(screen_key)

        if settings is None:
            return None

        settings.heading = heading
        settings.body = body
        settings.footer = footer
        settings.registration_url = registration_url
        settings.promo_code = promo_code
        settings.support_username = support_username

        await self._session.flush()
        return settings

    async def update_media(
        self,
        *,
        screen_key: str,
        media_file_id: str | None,
        media_type: str | None,
    ) -> ContentScreenSettings | None:
        settings = await self.get_by_key(screen_key)

        if settings is None:
            return None

        settings.media_file_id = media_file_id
        settings.media_type = media_type

        await self._session.flush()
        return settings

    async def set_active(
        self,
        *,
        screen_key: str,
        is_active: bool,
    ) -> ContentScreenSettings | None:
        settings = await self.get_by_key(screen_key)

        if settings is None:
            return None

        settings.is_active = is_active

        await self._session.flush()
        return settings
