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
