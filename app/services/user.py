from datetime import UTC, datetime

from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.db.models.user import User
from app.repositories.user import UserRepository


class UserService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def set_locale(
        self,
        *,
        user_id: int,
        locale: str,
    ) -> None:
        async with self._session_factory() as session:
            repository = UserRepository(session)

            await repository.update_locale(
                user_id=user_id,
                locale=locale,
                updated_at=datetime.now(UTC),
            )

            await session.commit()

    async def upsert_from_telegram(
        self,
        telegram_user: TelegramUser,
    ) -> User:
        async with self._session_factory() as session:
            repository = UserRepository(session)

            user = await repository.upsert(
                telegram_user_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
                locale=telegram_user.language_code or "en",
                is_bot=telegram_user.is_bot,
                now=datetime.now(UTC),
            )

            await session.commit()
            return user
