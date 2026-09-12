from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.user_onboarding import UserOnboarding


class OnboardingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(
        self,
        user_id: int,
    ) -> UserOnboarding | None:
        result = await self._session.execute(
            select(UserOnboarding).where(
                UserOnboarding.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        *,
        user_id: int,
    ) -> UserOnboarding:
        statement = (
            insert(UserOnboarding)
            .values(user_id=user_id)
            .on_conflict_do_nothing(
                index_elements=[UserOnboarding.user_id]
            )
        )

        await self._session.execute(statement)

        result = await self._session.execute(
            select(UserOnboarding).where(
                UserOnboarding.user_id == user_id
            )
        )

        return result.scalar_one()

    async def set_language_selected(
        self,
        *,
        user_id: int,
        selected_at: datetime,
    ) -> None:
        await self._session.execute(
            update(UserOnboarding)
            .where(UserOnboarding.user_id == user_id)
            .values(
                language_selected_at=selected_at,
                updated_at=selected_at,
            )
        )

    async def set_vip_category(
        self,
        *,
        user_id: int,
        vip_category_id: int,
        selected_at: datetime,
    ) -> None:
        await self._session.execute(
            update(UserOnboarding)
            .where(UserOnboarding.user_id == user_id)
            .values(
                vip_category_id=vip_category_id,
                category_selected_at=selected_at,
                updated_at=selected_at,
            )
        )

    async def set_registration_completed(
        self,
        *,
        user_id: int,
        completed_at: datetime,
    ) -> None:
        await self._session.execute(
            update(UserOnboarding)
            .where(UserOnboarding.user_id == user_id)
            .values(
                registration_completed_at=completed_at,
                updated_at=completed_at,
            )
        )

    async def set_contact_verified(
        self,
        *,
        user_id: int,
        verified_at: datetime,
    ) -> None:
        await self._session.execute(
            update(UserOnboarding)
            .where(UserOnboarding.user_id == user_id)
            .values(
                contact_verified_at=verified_at,
                updated_at=verified_at,
            )
        )
