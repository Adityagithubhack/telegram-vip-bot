from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.vip_menu_settings import VipMenuSettings


class VipMenuSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self) -> VipMenuSettings | None:
        result = await self._session.execute(
            select(VipMenuSettings).order_by(VipMenuSettings.id.asc()).limit(1)
        )
        return result.scalar_one_or_none()

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
    ) -> VipMenuSettings | None:
        settings = await self.get()

        if settings is None:
            return None

        settings.heading = heading
        settings.description = description
        settings.footer_text = footer_text
        settings.free_vs_vip_heading = free_vs_vip_heading
        settings.free_vs_vip_info = free_vs_vip_info
        settings.free_vs_vip_promo_code = free_vs_vip_promo_code
        settings.free_vs_vip_support_username = (
            free_vs_vip_support_username
        )
        settings.compare_heading = compare_heading
        settings.compare_intro = compare_intro
        settings.live_bets_heading = live_bets_heading
        settings.live_bets_info = live_bets_info
        settings.pre_match_bets_heading = pre_match_bets_heading
        settings.pre_match_bets_info = pre_match_bets_info

        await self._session.flush()
        return settings


    async def update_live_bets_media(
        self,
        *,
        media_file_id: str | None,
        media_type: str | None,
    ) -> VipMenuSettings | None:
        settings = await self.get()
        if settings is None:
            return None

        settings.live_bets_media_file_id = media_file_id
        settings.live_bets_media_type = media_type

        await self._session.flush()
        return settings

    async def update_pre_match_bets_media(
        self,
        *,
        media_file_id: str | None,
        media_type: str | None,
    ) -> VipMenuSettings | None:
        settings = await self.get()
        if settings is None:
            return None

        settings.pre_match_bets_media_file_id = media_file_id
        settings.pre_match_bets_media_type = media_type

        await self._session.flush()
        return settings
