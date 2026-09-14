from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.db.models.user_onboarding import UserOnboarding
from app.repositories.onboarding import OnboardingRepository


@dataclass(slots=True, frozen=True)
class PendingVipApproval:
    user_id: int


@dataclass(slots=True, frozen=True)
class VipGrantResult:
    granted: bool
    reason: str


@dataclass(slots=True, frozen=True)
class OnboardingProgress:
    completed_steps: int
    total_steps: int
    progress_percent: int
    next_step: str
    state: UserOnboarding


class OnboardingService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def select_language(
        self,
        *,
        user_id: int,
    ) -> None:
        async with self._session_factory() as session:
            repository = OnboardingRepository(session)

            await repository.get_or_create(
                user_id=user_id,
            )

            await repository.set_language_selected(
                user_id=user_id,
                selected_at=datetime.now(UTC),
            )

            await session.commit()


    async def select_vip_category(
        self,
        *,
        user_id: int,
        vip_category_id: int,
    ) -> None:
        async with self._session_factory() as session:
            repository = OnboardingRepository(session)

            await repository.get_or_create(
                user_id=user_id,
            )

            await repository.set_vip_category(
                user_id=user_id,
                vip_category_id=vip_category_id,
                selected_at=datetime.now(UTC),
            )

            await session.commit()

    async def complete_registration(
        self,
        *,
        user_id: int,
    ) -> None:
        completed_at = datetime.now(UTC)

        async with self._session_factory() as session:
            repository = OnboardingRepository(session)

            await repository.get_or_create(
                user_id=user_id,
            )

            await repository.set_registration_completed(
                user_id=user_id,
                completed_at=completed_at,
            )

            await session.commit()

    async def verify_contact(
        self,
        *,
        user_id: int,
    ) -> None:
        verified_at = datetime.now(UTC)

        async with self._session_factory() as session:
            repository = OnboardingRepository(session)

            await repository.get_or_create(
                user_id=user_id,
            )

            await repository.set_contact_verified(
                user_id=user_id,
                verified_at=verified_at,
            )

            await session.commit()

    async def grant_vip_access(
        self,
        *,
        user_id: int,
    ) -> VipGrantResult:
        async with self._session_factory() as session:
            repository = OnboardingRepository(session)

            state = await repository.get_by_user_id(
                user_id=user_id,
            )

            if state is None:
                return VipGrantResult(
                    granted=False,
                    reason="onboarding_not_found",
                )

            if state.vip_access_granted_at is not None:
                return VipGrantResult(
                    granted=False,
                    reason="already_granted",
                )

            if state.contact_verified_at is None:
                return VipGrantResult(
                    granted=False,
                    reason="contact_not_verified",
                )

            granted_at = datetime.now(UTC)

            await repository.set_vip_access_granted(
                user_id=user_id,
                granted_at=granted_at,
            )

            await session.commit()

            return VipGrantResult(
                granted=True,
                reason="granted",
            )

    async def revoke_vip_access(
        self,
        *,
        user_id: int,
    ) -> None:
        async with self._session_factory() as session:
            repository = OnboardingRepository(session)
            await repository.revoke_vip_access(
                user_id=user_id,
                updated_at=datetime.now(UTC),
            )
            await session.commit()

    async def reset_verification(
        self,
        *,
        user_id: int,
    ) -> None:
        async with self._session_factory() as session:
            repository = OnboardingRepository(session)
            await repository.reset_verification(
                user_id=user_id,
                updated_at=datetime.now(UTC),
            )
            await session.commit()

    async def reset_all_verifications(
        self,
    ) -> int:
        async with self._session_factory() as session:
            repository = OnboardingRepository(session)
            count = await repository.reset_all_verifications(
                updated_at=datetime.now(UTC),
            )
            await session.commit()
            return count

    async def get_state(
        self,
        *,
        user_id: int,
    ) -> UserOnboarding | None:
        async with self._session_factory() as session:
            repository = OnboardingRepository(session)
            return await repository.get_by_user_id(
                user_id=user_id
            )

    async def list_pending_vip_approvals(
        self,
    ) -> list[PendingVipApproval]:
        async with self._session_factory() as session:
            repository = OnboardingRepository(session)

            rows = await repository.list_pending_vip_approvals()

            return [
                PendingVipApproval(
                    user_id=row.user_id,
                )
                for row in rows
            ]

    async def get_progress(
        self,
        *,
        user_id: int,
    ) -> OnboardingProgress:
        async with self._session_factory() as session:
            repository = OnboardingRepository(session)

            state = await repository.get_or_create(
                user_id=user_id,
            )

            await session.commit()

        steps = [
            state.language_selected_at is not None,
            state.category_selected_at is not None,
            state.registration_completed_at is not None,
            state.contact_verified_at is not None,
            state.vip_access_granted_at is not None,
        ]

        completed_steps = sum(steps)
        total_steps = len(steps)

        progress_percent = int(
            completed_steps / total_steps * 100
        )

        if state.language_selected_at is None:
            next_step = "Select language"
        elif state.category_selected_at is None:
            next_step = "Select VIP category"
        elif state.registration_completed_at is None:
            next_step = "Complete registration"
        elif state.contact_verified_at is None:
            next_step = "Complete contact verification"
        elif state.vip_access_granted_at is None:
            next_step = "Wait for VIP access"
        else:
            next_step = "VIP access active"

        return OnboardingProgress(
            completed_steps=completed_steps,
            total_steps=total_steps,
            progress_percent=progress_percent,
            next_step=next_step,
            state=state,
        )
