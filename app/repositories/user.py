from datetime import datetime

from sqlalchemy import select
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
                    "locale": locale,
                    "is_bot": is_bot,
                    "is_active": True,
                    "last_seen_at": now,
                },
            )
            .returning(User)
        )

        result = await self._session.execute(statement)
        return result.scalar_one()
