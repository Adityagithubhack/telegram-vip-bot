from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.db.models.user_onboarding import UserOnboarding
from app.repositories.onboarding import OnboardingRepository


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
