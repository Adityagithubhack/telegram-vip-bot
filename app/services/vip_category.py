from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.vip_category import VipCategoryRepository


@dataclass(slots=True, frozen=True)
class VipCategoryItem:
    id: int
    code: str
    name_key: str
    description_key: str | None


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
                    name_key=category.name_key,
                    description_key=category.description_key,
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
                name_key=category.name_key,
                description_key=category.description_key,
            )
