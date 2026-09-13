from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.vip_category import VipCategoryRepository


@dataclass(slots=True, frozen=True)
class VipCategoryItem:
    id: int
    code: str
    display_name: str
    name_key: str
    description_key: str | None
    vip_info: str | None
    compare_info: str | None
    registration_url: str | None
    promo_code: str | None
    support_username: str | None
    media_file_id: str | None
    media_type: str | None
    is_active: bool


class VipCategoryService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def list_active(self) -> list[VipCategoryItem]:
        async with self._session_factory() as session:
            repository = VipCategoryRepository(session)

            categories = await repository.list_active()

            return [
                VipCategoryItem(
                    id=category.id,
                    code=category.code,
                    display_name=category.display_name,
                    name_key=category.name_key,
                    description_key=category.description_key,
                    vip_info=category.vip_info,
                    compare_info=category.compare_info,
                    registration_url=category.registration_url,
                    promo_code=category.promo_code,
                    support_username=category.support_username,
                    media_file_id=category.media_file_id,
                    media_type=category.media_type,
                    is_active=category.is_active,
                )
                for category in categories
            ]

    async def get_by_id(
        self,
        *,
        category_id: int,
    ) -> VipCategoryItem | None:
        async with self._session_factory() as session:
            repository = VipCategoryRepository(session)

            category = await repository.get_by_id(category_id)

            if category is None:
                return None

            return VipCategoryItem(
                id=category.id,
                code=category.code,
                display_name=category.display_name,
                name_key=category.name_key,
                description_key=category.description_key,
                vip_info=category.vip_info,
                compare_info=category.compare_info,
                registration_url=category.registration_url,
                promo_code=category.promo_code,
                support_username=category.support_username,
                media_file_id=category.media_file_id,
                media_type=category.media_type,
                is_active=category.is_active,
            )

    async def update_registration_url(
        self,
        *,
        category_id: int,
        registration_url: str | None,
    ) -> bool:
        async with self._session_factory() as session:
            repository = VipCategoryRepository(session)

            category = await repository.update_registration_url(
                category_id=category_id,
                registration_url=registration_url,
            )

            if category is None:
                return False

            await session.commit()
            return True

    async def update_promo_code(
        self,
        *,
        category_id: int,
        promo_code: str | None,
    ) -> bool:
        async with self._session_factory() as session:
            repository = VipCategoryRepository(session)

            category = await repository.update_promo_code(
                category_id=category_id,
                promo_code=promo_code,
            )

            if category is None:
                return False

            await session.commit()
            return True

    async def update_media(
        self,
        *,
        category_id: int,
        media_file_id: str | None,
        media_type: str | None,
    ) -> bool:
        async with self._session_factory() as session:
            repository = VipCategoryRepository(session)

            category = await repository.update_media(
                category_id=category_id,
                media_file_id=media_file_id,
                media_type=media_type,
            )

            if category is None:
                return False

            await session.commit()
            return True

    async def update_support_username(
        self,
        *,
        category_id: int,
        support_username: str | None,
    ) -> bool:
        async with self._session_factory() as session:
            repository = VipCategoryRepository(session)

            category = await repository.update_support_username(
                category_id=category_id,
                support_username=support_username,
            )

            if category is None:
                return False

            await session.commit()
            return True

    async def update_vip_info(
        self,
        *,
        category_id: int,
        vip_info: str | None,
    ) -> bool:
        async with self._session_factory() as session:
            repository = VipCategoryRepository(session)

            category = await repository.update_vip_info(
                category_id=category_id,
                vip_info=vip_info,
            )

            if category is None:
                return False

            await session.commit()
            return True

    async def update_display_name(
        self,
        *,
        category_id: int,
        display_name: str,
    ) -> bool:
        async with self._session_factory() as session:
            repository = VipCategoryRepository(session)

            category = await repository.update_display_name(
                category_id=category_id,
                display_name=display_name,
            )

            if category is None:
                return False

            await session.commit()
            return True

    async def update_compare_info(
        self,
        *,
        category_id: int,
        compare_info: str | None,
    ) -> bool:
        async with self._session_factory() as session:
            repository = VipCategoryRepository(session)

            category = await repository.update_compare_info(
                category_id=category_id,
                compare_info=compare_info,
            )

            if category is None:
                return False

            await session.commit()
            return True

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
    ) -> bool:
        async with self._session_factory() as session:
            repository = VipCategoryRepository(session)

            await repository.create(
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
            )

            await session.commit()
            return True

    async def set_active(
        self,
        *,
        category_id: int,
        is_active: bool,
    ) -> bool:
        async with self._session_factory() as session:
            repository = VipCategoryRepository(session)

            category = await repository.set_active(
                category_id=category_id,
                is_active=is_active,
            )

            if category is None:
                return False

            await session.commit()
            return True

    async def list_all(self) -> list[VipCategoryItem]:
        async with self._session_factory() as session:
            repository = VipCategoryRepository(session)
            categories = await repository.list_all()

            return [
                VipCategoryItem(
                    id=category.id,
                    code=category.code,
                    display_name=category.display_name,
                    name_key=category.name_key,
                    description_key=category.description_key,
                    vip_info=category.vip_info,
                    compare_info=category.compare_info,
                    registration_url=category.registration_url,
                    promo_code=category.promo_code,
                    support_username=category.support_username,
                    media_file_id=category.media_file_id,
                    media_type=category.media_type,
                    is_active=category.is_active,
                )
                for category in categories
            ]

    async def get_any_by_id(
        self,
        *,
        category_id: int,
    ) -> VipCategoryItem | None:
        async with self._session_factory() as session:
            repository = VipCategoryRepository(session)
            category = await repository.get_any_by_id(category_id)

            if category is None:
                return None

            return VipCategoryItem(
                id=category.id,
                code=category.code,
                display_name=category.display_name,
                name_key=category.name_key,
                description_key=category.description_key,
                vip_info=category.vip_info,
                compare_info=category.compare_info,
                registration_url=category.registration_url,
                promo_code=category.promo_code,
                support_username=category.support_username,
                media_file_id=category.media_file_id,
                media_type=category.media_type,
                is_active=category.is_active,
            )

    async def move(
        self,
        *,
        category_id: int,
        direction: str,
    ) -> bool:
        async with self._session_factory() as session:
            repository = VipCategoryRepository(session)
            categories = await repository.list_all()

            current_index = next(
                (
                    index
                    for index, category in enumerate(categories)
                    if category.id == category_id
                ),
                None,
            )

            if current_index is None:
                return False

            if direction == "up":
                target_index = current_index - 1
            elif direction == "down":
                target_index = current_index + 1
            else:
                return False

            if target_index < 0 or target_index >= len(categories):
                return False

            current = categories[current_index]
            target = categories[target_index]

            current_order = current.sort_order
            target_order = target.sort_order

            await repository.update_sort_order(
                category_id=current.id,
                sort_order=target_order,
            )

            await repository.update_sort_order(
                category_id=target.id,
                sort_order=current_order,
            )

            await session.commit()
            return True
