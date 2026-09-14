from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.bot_admin import BotAdmin


class BotAdminRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(
        self,
        telegram_user_id: int,
    ) -> BotAdmin | None:
        result = await self._session.execute(
            select(BotAdmin).where(
                BotAdmin.telegram_user_id == telegram_user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[BotAdmin]:
        result = await self._session.execute(
            select(BotAdmin).order_by(
                BotAdmin.role.desc(),
                BotAdmin.id.asc(),
            )
        )
        return list(result.scalars().all())


    async def add(
        self,
        telegram_user_id: int,
        role: str = "admin",
    ) -> BotAdmin:
        admin = BotAdmin(
            telegram_user_id=telegram_user_id,
            role=role,
            is_active=True,
        )
        self._session.add(admin)
        await self._session.flush()
        return admin

    async def set_active(
        self,
        telegram_user_id: int,
        is_active: bool,
    ) -> BotAdmin | None:
        admin = await self.get_by_telegram_id(telegram_user_id)

        if admin is None:
            return None

        admin.is_active = is_active
        await self._session.flush()
        return admin

    async def delete(
        self,
        telegram_user_id: int,
    ) -> bool:
        admin = await self.get_by_telegram_id(
            telegram_user_id
        )

        if admin is None:
            return False

        await self._session.delete(admin)
        await self._session.flush()

        return True


    async def set_timezone(
        self,
        telegram_user_id: int,
        timezone: str,
    ) -> BotAdmin | None:
        admin = await self.get_by_telegram_id(
            telegram_user_id
        )

        if admin is None:
            return None

        admin.timezone = timezone
        await self._session.flush()

        return admin
