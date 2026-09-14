from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.referral import ReferralRepository
from app.infra.db.models.user import User


@dataclass(slots=True, frozen=True)
class ReferralInfo:
    referral_code: str
    friends_joined: int
    commission_percent: int
    vip_link: str | None
    promo_code: str | None
    claim_username: str | None
    referred_users: list[User]


class ReferralService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get_info(
        self,
        *,
        user_id: int,
    ) -> ReferralInfo:
        async with self._session_factory() as session:
            repository = ReferralRepository(session)

            referral = await repository.get_or_create(user_id)
            settings = (
                await repository.get_or_create_program_settings()
            )
            friends_joined = await repository.count_referred_users(
                user_id
            )
            referred_users = await repository.get_referred_users(
                user_id
            )

            await session.commit()

            return ReferralInfo(
                referral_code=referral.referral_code,
                friends_joined=friends_joined,
                commission_percent=settings.commission_percent,
                vip_link=settings.vip_link,
                promo_code=settings.promo_code,
                claim_username=settings.claim_username,
                referred_users=referred_users,
            )

    async def attribute(
        self,
        *,
        user_id: int,
        referral_code: str,
    ) -> bool:
        async with self._session_factory() as session:
            repository = ReferralRepository(session)

            referrer = await repository.get_by_code(
                referral_code
            )
            if referrer is None:
                return False

            attributed = await repository.attribute_referral(
                user_id=user_id,
                referrer_user_id=referrer.user_id,
            )

            if attributed:
                await session.commit()
            else:
                await session.rollback()

            return attributed


    async def get_referral_leaderboard(
        self,
    ) -> list[tuple[User, int]]:
        async with self._session_factory() as session:
            repository = ReferralRepository(session)
            leaderboard = await repository.get_referral_leaderboard()
            return leaderboard

    async def get_program_settings(self) -> ReferralInfo:
        async with self._session_factory() as session:
            repository = ReferralRepository(session)
            settings = (
                await repository.get_or_create_program_settings()
            )

            await session.commit()

            return ReferralInfo(
                referral_code="",
                friends_joined=0,
                commission_percent=settings.commission_percent,
                vip_link=settings.vip_link,
                promo_code=settings.promo_code,
                claim_username=settings.claim_username,
                referred_users=[],
            )

    async def update_program_settings(
        self,
        *,
        commission_percent: int | None = None,
        vip_link: str | None = None,
        promo_code: str | None = None,
        claim_username: str | None = None,
    ) -> ReferralInfo:
        async with self._session_factory() as session:
            repository = ReferralRepository(session)

            settings = await repository.update_program_settings(
                commission_percent=commission_percent,
                vip_link=vip_link,
                promo_code=promo_code,
                claim_username=claim_username,
            )

            await session.commit()

            return ReferralInfo(
                referral_code="",
                friends_joined=0,
                commission_percent=settings.commission_percent,
                vip_link=settings.vip_link,
                promo_code=settings.promo_code,
                claim_username=settings.claim_username,
                referred_users=[],
            )
