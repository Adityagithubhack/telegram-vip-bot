from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.audit_log import AuditLogRepository
from app.repositories.onboarding import OnboardingRepository
from app.repositories.user import UserRepository


@dataclass(slots=True, frozen=True)
class AdminVipApprovalResult:
    granted: bool
    reason: str
    telegram_user_id: int | None = None


class AdminVipService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def approve_vip(
        self,
        *,
        actor_telegram_user_id: int,
        user_id: int,
    ) -> AdminVipApprovalResult:
        async with self._session_factory() as session:
            onboarding_repository = OnboardingRepository(session)
            audit_repository = AuditLogRepository(session)
            user_repository = UserRepository(session)

            state = await onboarding_repository.get_by_user_id(
                user_id=user_id,
            )

            if state is None:
                return AdminVipApprovalResult(
                    granted=False,
                    reason="onboarding_not_found",
                )

            if state.vip_access_granted_at is not None:
                return AdminVipApprovalResult(
                    granted=False,
                    reason="already_granted",
                )

            if state.contact_verified_at is None:
                return AdminVipApprovalResult(
                    granted=False,
                    reason="contact_not_verified",
                )

            granted_at = datetime.now(UTC)

            await onboarding_repository.set_vip_access_granted(
                user_id=user_id,
                granted_at=granted_at,
            )

            audit_repository.add(
                actor_telegram_user_id=actor_telegram_user_id,
                action="vip_access_granted",
                target_type="user",
                target_id=str(user_id),
                details="VIP access granted by super admin",
            )

            user = await user_repository.get_by_id(user_id=user_id)

            await session.commit()

            return AdminVipApprovalResult(
                granted=True,
                reason="granted",
                telegram_user_id=user.telegram_user_id if user is not None else None,
            )
