from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(
        self,
        telegram_user_id: int,
    ) -> User | None:
        result = await self._session.execute(
            select(User).where(
                User.telegram_user_id == telegram_user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_username(
        self,
        username: str,
    ) -> User | None:
        clean_username = username.lstrip("@")

        result = await self._session.execute(
            select(User).where(
                User.username.ilike(clean_username)
            )
        )

        return result.scalar_one_or_none()

    async def update_locale(
        self,
        *,
        user_id: int,
        locale: str,
        updated_at: datetime,
    ) -> None:
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                locale=locale,
                updated_at=updated_at,
            )
        )

    async def upsert(
        self,
        *,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        locale: str,
        is_bot: bool,
        now: datetime,
    ) -> User:
        statement = (
            insert(User)
            .values(
                telegram_user_id=telegram_user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                locale=locale,
                is_bot=is_bot,
                is_active=True,
                first_seen_at=now,
                last_seen_at=now,
            )
            .on_conflict_do_update(
                index_elements=[User.telegram_user_id],
                set_={
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_bot": is_bot,
                    "is_active": True,
                    "last_seen_at": now,
                    "updated_at": now,
                },
            )
            .returning(User)
        )

        result = await self._session.execute(statement)
        return result.scalar_one()

    async def get_by_id(
        self,
        *,
        user_id: int,
    ) -> User | None:
        result = await self._session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[User]:
        result = await self._session.execute(
            select(User)
            .order_by(
                User.created_at.desc(),
                User.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_ids(
        self,
        user_ids: list[int],
    ) -> list[User]:
        if not user_ids:
            return []

        result = await self._session.execute(
            select(User).where(
                User.id.in_(user_ids)
            )
        )

        return list(result.scalars().all())


    async def delete(
        self,
        user_id: int,
    ) -> bool:
        user = await self.get_by_id(user_id=user_id)

        if user is None:
            return False

        await self._session.delete(user)
        await self._session.flush()

        return True
