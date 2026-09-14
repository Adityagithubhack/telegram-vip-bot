from datetime import datetime, timezone
from secrets import token_hex

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models.referral import (
    ReferralProgramSettings,
    UserReferral,
)
from app.infra.db.models.user import User


class ReferralRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(
        self,
        user_id: int,
    ) -> UserReferral | None:
        result = await self._session.execute(
            select(UserReferral).where(
                UserReferral.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_code(
        self,
        referral_code: str,
    ) -> UserReferral | None:
        result = await self._session.execute(
            select(UserReferral).where(
                UserReferral.referral_code == referral_code
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        user_id: int,
    ) -> UserReferral:
        existing = await self.get_by_user_id(user_id)
        if existing is not None:
            return existing

        while True:
            code = token_hex(4)
            existing_code = await self.get_by_code(code)
            if existing_code is None:
                break

        referral = UserReferral(
            user_id=user_id,
            referral_code=code,
        )
        self._session.add(referral)
        await self._session.flush()
        return referral

    async def attribute_referral(
        self,
        *,
        user_id: int,
        referrer_user_id: int,
    ) -> bool:
        if user_id == referrer_user_id:
            return False

        referral = await self.get_or_create(user_id)

        if referral.referred_by_user_id is not None:
            return False

        referral.referred_by_user_id = referrer_user_id
        referral.referred_at = datetime.now(timezone.utc)
        await self._session.flush()
        return True

    async def get_referred_users(
        self,
        referrer_user_id: int,
    ) -> list[User]:
        result = await self._session.execute(
            select(User)
            .join(
                UserReferral,
                UserReferral.user_id == User.id,
            )
            .where(
                UserReferral.referred_by_user_id
                == referrer_user_id
            )
            .order_by(
                UserReferral.referred_at.asc()
            )
        )
        return list(result.scalars().all())

    async def count_referred_users(
        self,
        referrer_user_id: int,
    ) -> int:
        result = await self._session.execute(
            select(func.count(UserReferral.id)).where(
                UserReferral.referred_by_user_id
                == referrer_user_id
            )
        )
        return int(result.scalar_one())

    async def get_referral_leaderboard(
        self,
    ) -> list[tuple[User, int]]:
        result = await self._session.execute(
            select(
                User,
                func.count(UserReferral.id).label(
                    "referral_count"
                ),
            )
            .join(
                UserReferral,
                UserReferral.user_id == User.id,
            )
            .where(
                UserReferral.referred_by_user_id.is_not(None)
            )
            .group_by(User.id)
            .order_by(
                func.count(UserReferral.id).desc()
            )
        )

        return [
            (user, int(count))
            for user, count in result.all()
        ]

    async def get_program_settings(
        self,
    ) -> ReferralProgramSettings | None:
        result = await self._session.execute(
            select(ReferralProgramSettings)
            .order_by(ReferralProgramSettings.id.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_or_create_program_settings(
        self,
    ) -> ReferralProgramSettings:
        settings = await self.get_program_settings()
        if settings is not None:
            return settings

        settings = ReferralProgramSettings()
        self._session.add(settings)
        await self._session.flush()
        return settings


    async def update_program_settings(
        self,
        *,
        commission_percent: int | None = None,
        vip_link: str | None = None,
        promo_code: str | None = None,
        claim_username: str | None = None,
    ) -> ReferralProgramSettings:
        settings = await self.get_or_create_program_settings()

        if commission_percent is not None:
            settings.commission_percent = commission_percent

        if vip_link is not None:
            settings.vip_link = vip_link

        if promo_code is not None:
            settings.promo_code = promo_code

        if claim_username is not None:
            settings.claim_username = claim_username

        await self._session.flush()
        return settings
