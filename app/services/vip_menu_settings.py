from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.vip_menu_settings import VipMenuSettingsRepository


@dataclass(slots=True, frozen=True)
class VipMenuSettingsItem:
    heading: str
    description: str | None
    footer_text: str
    free_vs_vip_heading: str | None
    free_vs_vip_info: str | None
    free_vs_vip_promo_code: str | None
    free_vs_vip_support_username: str | None
    compare_heading: str | None
    compare_intro: str | None
    live_bets_heading: str | None
    live_bets_info: str | None
    pre_match_bets_heading: str | None
    pre_match_bets_info: str | None
    live_bets_media_file_id: str | None
    live_bets_media_type: str | None
    pre_match_bets_media_file_id: str | None
    pre_match_bets_media_type: str | None


class VipMenuSettingsService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get(self) -> VipMenuSettingsItem | None:
        async with self._session_factory() as session:
            repository = VipMenuSettingsRepository(session)
            settings = await repository.get()

            if settings is None:
                return None

            return VipMenuSettingsItem(
                heading=settings.heading,
                description=settings.description,
                footer_text=settings.footer_text,
                free_vs_vip_heading=settings.free_vs_vip_heading,
                free_vs_vip_info=settings.free_vs_vip_info,
                free_vs_vip_promo_code=settings.free_vs_vip_promo_code,
                free_vs_vip_support_username=(
                    settings.free_vs_vip_support_username
                ),
                compare_heading=settings.compare_heading,
                compare_intro=settings.compare_intro,
                live_bets_heading=settings.live_bets_heading,
                live_bets_info=settings.live_bets_info,
                pre_match_bets_heading=settings.pre_match_bets_heading,
                pre_match_bets_info=settings.pre_match_bets_info,
                live_bets_media_file_id=settings.live_bets_media_file_id,
                live_bets_media_type=settings.live_bets_media_type,
                pre_match_bets_media_file_id=(
                    settings.pre_match_bets_media_file_id
                ),
                pre_match_bets_media_type=settings.pre_match_bets_media_type,
            )

    async def update(
        self,
        *,
        heading: str,
        description: str | None,
        footer_text: str,
        free_vs_vip_heading: str | None,
        free_vs_vip_info: str | None,
        free_vs_vip_promo_code: str | None,
        free_vs_vip_support_username: str | None,
        compare_heading: str | None,
        compare_intro: str | None,
        live_bets_heading: str | None,
        live_bets_info: str | None,
        pre_match_bets_heading: str | None,
        pre_match_bets_info: str | None,
    ) -> bool:
        async with self._session_factory() as session:
            repository = VipMenuSettingsRepository(session)

            settings = await repository.update(
                heading=heading,
                description=description,
                footer_text=footer_text,
                free_vs_vip_heading=free_vs_vip_heading,
                free_vs_vip_info=free_vs_vip_info,
                free_vs_vip_promo_code=free_vs_vip_promo_code,
                free_vs_vip_support_username=(
                    free_vs_vip_support_username
                ),
                compare_heading=compare_heading,
                compare_intro=compare_intro,
                live_bets_heading=live_bets_heading,
                live_bets_info=live_bets_info,
                pre_match_bets_heading=pre_match_bets_heading,
                pre_match_bets_info=pre_match_bets_info,
            )

            if settings is None:
                return False

            await session.commit()
            return True

    async def update_live_bets_media(
        self,
        *,
        media_file_id: str | None,
        media_type: str | None,
    ) -> bool:
        async with self._session_factory() as session:
            repository = VipMenuSettingsRepository(session)

            settings = await repository.update_live_bets_media(
                media_file_id=media_file_id,
                media_type=media_type,
            )

            if settings is None:
                return False

            await session.commit()
            return True

    async def update_pre_match_bets_media(
        self,
        *,
        media_file_id: str | None,
        media_type: str | None,
    ) -> bool:
        async with self._session_factory() as session:
            repository = VipMenuSettingsRepository(session)

            settings = await repository.update_pre_match_bets_media(
                media_file_id=media_file_id,
                media_type=media_type,
            )

            if settings is None:
                return False

            await session.commit()
            return True

