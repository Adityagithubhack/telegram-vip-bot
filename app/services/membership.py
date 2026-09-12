from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.gateways.telegram_membership import TelegramMembershipGateway
from app.infra.db.models.channel import Channel
from app.infra.db.models.user import User
from app.repositories.channel import ChannelRepository
from app.repositories.membership import MembershipRepository


@dataclass(slots=True, frozen=True)
class ChannelMembershipDecision:
    channel_id: int
    telegram_chat_id: int
    title: str
    username: str | None
    invite_url: str | None
    status: str | None
    is_satisfied: bool
    error: str | None


@dataclass(slots=True, frozen=True)
class MembershipDecision:
    all_required_joined: bool
    channels: list[ChannelMembershipDecision]


class MembershipService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        gateway: TelegramMembershipGateway,
    ) -> None:
        self._session_factory = session_factory
        self._gateway = gateway

    async def check_required_channels(
        self,
        *,
        user: User,
    ) -> MembershipDecision:
        async with self._session_factory() as session:
            channel_repository = ChannelRepository(session)
            membership_repository = MembershipRepository(session)

            channels = await channel_repository.get_required_active()
            decisions: list[ChannelMembershipDecision] = []

            for channel in channels:
                decision = await self._check_channel(
                    user=user,
                    channel=channel,
                    repository=membership_repository,
                )
                decisions.append(decision)

            await session.commit()

        return MembershipDecision(
            all_required_joined=all(
                item.is_satisfied
                for item in decisions
            ),
            channels=decisions,
        )

    async def _check_channel(
        self,
        *,
        user: User,
        channel: Channel,
        repository: MembershipRepository,
    ) -> ChannelMembershipDecision:
        started = perf_counter()

        result = await self._gateway.get_membership(
            chat_id=channel.telegram_chat_id,
            user_id=user.telegram_user_id,
        )

        latency_ms = int(
            (perf_counter() - started) * 1000
        )
        checked_at = datetime.now(UTC)

        await repository.add_check(
            user_id=user.id,
            channel_id=channel.id,
            telegram_status=result.status,
            is_satisfied=result.is_satisfied,
            source="telegram_api",
            error=result.error,
            latency_ms=latency_ms,
            checked_at=checked_at,
        )

        if result.status is not None:
            await repository.upsert_latest(
                user_id=user.id,
                channel_id=channel.id,
                telegram_status=result.status,
                is_satisfied=result.is_satisfied,
                checked_at=checked_at,
                expires_at=None,
            )

        return ChannelMembershipDecision(
            channel_id=channel.id,
            telegram_chat_id=channel.telegram_chat_id,
            title=channel.title,
            username=channel.username,
            invite_url=channel.invite_url,
            status=result.status,
            is_satisfied=result.is_satisfied,
            error=result.error,
        )
