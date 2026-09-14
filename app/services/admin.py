from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.db.models.bot_admin import BotAdmin
from app.repositories.bot_admin import BotAdminRepository


class AdminService:

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get_admin(
        self,
        telegram_user_id: int,
    ) -> BotAdmin | None:
        async with self._session_factory() as session:
            repository = BotAdminRepository(session)
            return await repository.get_by_telegram_id(
                telegram_user_id
            )

    async def ensure_owner(
        self,
        telegram_user_id: int,
    ) -> BotAdmin:
        async with self._session_factory() as session:
            repository = BotAdminRepository(session)

            existing = await repository.get_by_telegram_id(
                telegram_user_id
            )

            if existing is not None:
                existing.role = "owner"
                existing.is_active = True
                await session.commit()
                await session.refresh(existing)
                return existing

            owner = await repository.add(
                telegram_user_id=telegram_user_id,
                role="owner",
            )
            await session.commit()
            await session.refresh(owner)
            return owner

    async def is_owner(
        self,
        telegram_user_id: int,
    ) -> bool:
        admin = await self.get_admin(telegram_user_id)

        return (
            admin is not None
            and admin.is_active
            and admin.role == "owner"
        )

    async def is_admin(
        self,
        telegram_user_id: int,
    ) -> bool:
        admin = await self.get_admin(telegram_user_id)

        return (
            admin is not None
            and admin.is_active
            and admin.role in {"owner", "admin"}
        )

    async def list_admins(self) -> list[BotAdmin]:
        async with self._session_factory() as session:
            repository = BotAdminRepository(session)
            return await repository.list_all()


    async def add_admin(
        self,
        telegram_user_id: int,
    ) -> BotAdmin:
        async with self._session_factory() as session:
            repository = BotAdminRepository(session)

            existing = await repository.get_by_telegram_id(
                telegram_user_id
            )

            if existing is not None:
                existing.role = "admin"
                existing.is_active = True
                await session.commit()
                await session.refresh(existing)
                return existing

            admin = await repository.add(
                telegram_user_id=telegram_user_id,
                role="admin",
            )

            await session.commit()
            await session.refresh(admin)

            return admin

    async def set_admin_active(
        self,
        telegram_user_id: int,
        is_active: bool,
    ) -> BotAdmin | None:
        async with self._session_factory() as session:
            repository = BotAdminRepository(session)

            admin = await repository.set_active(
                telegram_user_id=telegram_user_id,
                is_active=is_active,
            )

            if admin is None:
                return None

            await session.commit()
            await session.refresh(admin)

            return admin


    async def delete_admin(
        self,
        telegram_user_id: int,
    ) -> bool:
        async with self._session_factory() as session:
            repository = BotAdminRepository(session)

            admin = await repository.get_by_telegram_id(
                telegram_user_id
            )

            if admin is None:
                return False

            if admin.role == "owner":
                return False

            deleted = await repository.delete(
                telegram_user_id
            )

            if deleted:
                await session.commit()

            return deleted


    async def transfer_ownership(
        self,
        *,
        current_owner_telegram_user_id: int,
        new_owner_telegram_user_id: int,
    ) -> bool:
        if current_owner_telegram_user_id == new_owner_telegram_user_id:
            return False

        async with self._session_factory() as session:
            repository = BotAdminRepository(session)

            current_owner = await repository.get_by_telegram_id(
                current_owner_telegram_user_id
            )
            new_owner = await repository.get_by_telegram_id(
                new_owner_telegram_user_id
            )

            if (
                current_owner is None
                or current_owner.role != "owner"
                or not current_owner.is_active
            ):
                return False

            if (
                new_owner is None
                or new_owner.role != "admin"
                or not new_owner.is_active
            ):
                return False

            current_owner.role = "admin"
            new_owner.role = "owner"

            await session.commit()
            return True

    async def set_timezone(
        self,
        telegram_user_id: int,
        timezone: str,
    ) -> BotAdmin | None:
        async with self._session_factory() as session:
            repository = BotAdminRepository(session)

            admin = await repository.set_timezone(
                telegram_user_id=telegram_user_id,
                timezone=timezone,
            )

            if admin is None:
                return None

            await session.commit()
            await session.refresh(admin)

            return admin
