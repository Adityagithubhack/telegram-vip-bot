from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.audit_log import AuditLogRepository


class AuditLogService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def record(
        self,
        *,
        actor_telegram_user_id: int,
        action: str,
        target_type: str,
        target_id: str,
        details: str | None = None,
    ) -> None:
        async with self._session_factory() as session:
            repository = AuditLogRepository(session)

            repository.add(
                actor_telegram_user_id=actor_telegram_user_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                details=details,
            )

            await session.commit()


    async def list_recent(
        self,
        *,
        limit: int = 20,
    ):
        async with self._session_factory() as session:
            repository = AuditLogRepository(session)
            return await repository.list_recent(
                limit=limit
            )
