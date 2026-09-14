from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.content_screen_settings import (
    ContentScreenSettingsRepository,
)


@dataclass(slots=True, frozen=True)
class ContentScreenSettingsItem:
    screen_key: str
    heading: str | None
    body: str | None
    footer: str | None
    media_file_id: str | None
    media_type: str | None
    registration_url: str | None
    promo_code: str | None
    support_username: str | None
    is_active: bool


class ContentScreenSettingsService:

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get(
        self,
        screen_key: str,
    ) -> ContentScreenSettingsItem | None:
        async with self._session_factory() as session:
            repository = ContentScreenSettingsRepository(session)

            settings = await repository.get_by_key(screen_key)

            if settings is None:
                return None

            return ContentScreenSettingsItem(
                screen_key=settings.screen_key,
                heading=settings.heading,
                body=settings.body,
                footer=settings.footer,
                media_file_id=settings.media_file_id,
                media_type=settings.media_type,
                registration_url=settings.registration_url,
                promo_code=settings.promo_code,
                support_username=settings.support_username,
                is_active=settings.is_active,
            )

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
    ) -> bool:
        async with self._session_factory() as session:
            repository = ContentScreenSettingsRepository(session)

            settings = await repository.update_content(
                screen_key=screen_key,
                heading=heading,
                body=body,
                footer=footer,
                registration_url=registration_url,
                promo_code=promo_code,
                support_username=support_username,
            )

            if settings is None:
                return False

            await session.commit()
            return True

    async def update_media(
        self,
        *,
        screen_key: str,
        media_file_id: str | None,
        media_type: str | None,
    ) -> bool:
        async with self._session_factory() as session:
            repository = ContentScreenSettingsRepository(session)

            settings = await repository.update_media(
                screen_key=screen_key,
                media_file_id=media_file_id,
                media_type=media_type,
            )

            if settings is None:
                return False

            await session.commit()
            return True

    async def set_active(
        self,
        *,
        screen_key: str,
        is_active: bool,
    ) -> bool:
        async with self._session_factory() as session:
            repository = ContentScreenSettingsRepository(session)

            settings = await repository.set_active(
                screen_key=screen_key,
                is_active=is_active,
            )

            if settings is None:
                return False

            await session.commit()
            return True
