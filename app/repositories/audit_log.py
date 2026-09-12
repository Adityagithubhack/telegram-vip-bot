from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(
        self,
        *,
        actor_telegram_user_id: int,
        action: str,
        target_type: str,
        target_id: str,
        details: str | None = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            actor_telegram_user_id=actor_telegram_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )

        self._session.add(audit_log)

        return audit_log
