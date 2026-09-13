from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.vip_category import VipCategory


class VipCategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self) -> list[VipCategory]:
        result = await self._session.execute(
            select(VipCategory)
            .where(VipCategory.is_active.is_(True))
            .order_by(
                VipCategory.sort_order.asc(),
                VipCategory.id.asc(),
            )
        )

        return list(result.scalars().all())

    async def get_by_id(
        self,
        category_id: int,
    ) -> VipCategory | None:
        result = await self._session.execute(
            select(VipCategory).where(
                VipCategory.id == category_id,
                VipCategory.is_active.is_(True),
            )
        )

        return result.scalar_one_or_none()

    async def update_registration_url(
        self,
        *,
        category_id: int,
        registration_url: str | None,
    ) -> VipCategory | None:
        category = await self._session.get(VipCategory, category_id)

        if category is None:
            return None

        category.registration_url = registration_url
        await self._session.flush()
        return category

    async def update_promo_code(
        self,
        *,
        category_id: int,
        promo_code: str | None,
    ) -> VipCategory | None:
        category = await self._session.get(VipCategory, category_id)

        if category is None:
            return None

        category.promo_code = promo_code
        await self._session.flush()
        return category

    async def update_media(
        self,
        *,
        category_id: int,
        media_file_id: str | None,
        media_type: str | None,
    ) -> VipCategory | None:
        category = await self._session.get(VipCategory, category_id)

        if category is None:
            return None

        category.media_file_id = media_file_id
        category.media_type = media_type
        await self._session.flush()
        return category

    async def update_support_username(
        self,
        *,
        category_id: int,
        support_username: str | None,
    ) -> VipCategory | None:
        category = await self._session.get(VipCategory, category_id)

        if category is None:
            return None

        category.support_username = support_username
        await self._session.flush()
        return category

    async def update_vip_info(
        self,
        *,
        category_id: int,
        vip_info: str | None,
    ) -> VipCategory | None:
        category = await self._session.get(VipCategory, category_id)

        if category is None:
            return None

        category.vip_info = vip_info
        await self._session.flush()
        return category

    async def update_compare_info(
        self,
        *,
        category_id: int,
        compare_info: str | None,
    ) -> VipCategory | None:
        category = await self._session.get(VipCategory, category_id)

        if category is None:
            return None

        category.compare_info = compare_info
        await self._session.flush()
        return category

    async def update_display_name(
        self,
        *,
        category_id: int,
        display_name: str,
    ) -> VipCategory | None:
        category = await self._session.get(VipCategory, category_id)

        if category is None:
            return None

        category.display_name = display_name
        await self._session.flush()
        return category

    async def create(
        self,
        *,
        code: str,
        display_name: str,
        name_key: str,
        sort_order: int,
        vip_info: str | None = None,
        compare_info: str | None = None,
        registration_url: str | None = None,
        promo_code: str | None = None,
        support_username: str | None = None,
        media_file_id: str | None = None,
        media_type: str | None = None,
    ) -> VipCategory:
        category = VipCategory(
            code=code,
            display_name=display_name,
            name_key=name_key,
            sort_order=sort_order,
            vip_info=vip_info,
            compare_info=compare_info,
            registration_url=registration_url,
            promo_code=promo_code,
            support_username=support_username,
            media_file_id=media_file_id,
            media_type=media_type,
            is_active=True,
        )

        self._session.add(category)
        await self._session.flush()

        return category

    async def set_active(
        self,
        *,
        category_id: int,
        is_active: bool,
    ) -> VipCategory | None:
        category = await self._session.get(VipCategory, category_id)

        if category is None:
            return None

        category.is_active = is_active
        await self._session.flush()
        return category

    async def list_all(self) -> list[VipCategory]:
        result = await self._session.execute(
            select(VipCategory).order_by(
                VipCategory.sort_order.asc(),
                VipCategory.id.asc(),
            )
        )
        return list(result.scalars().all())

    async def get_any_by_id(
        self,
        category_id: int,
    ) -> VipCategory | None:
        return await self._session.get(
            VipCategory,
            category_id,
        )

    async def update_sort_order(
        self,
        *,
        category_id: int,
        sort_order: int,
    ) -> VipCategory | None:
        category = await self._session.get(VipCategory, category_id)

        if category is None:
            return None

        category.sort_order = sort_order
        await self._session.flush()
        return category
