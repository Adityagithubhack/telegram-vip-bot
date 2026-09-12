from dataclasses import dataclass

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatMemberRestricted


@dataclass(slots=True, frozen=True)
class MembershipResult:
    status: str | None
    is_satisfied: bool
    error: str | None = None


class TelegramMembershipGateway:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def get_membership(
        self,
        *,
        chat_id: int,
        user_id: int,
    ) -> MembershipResult:
        try:
            member = await self._bot.get_chat_member(
                chat_id=chat_id,
                user_id=user_id,
            )
        except TelegramAPIError as exc:
            return MembershipResult(
                status=None,
                is_satisfied=False,
                error=str(exc),
            )

        status = str(member.status)

        if isinstance(member, ChatMemberRestricted):
            is_satisfied = member.is_member
        else:
            is_satisfied = status in {
                ChatMemberStatus.CREATOR.value,
                ChatMemberStatus.ADMINISTRATOR.value,
                ChatMemberStatus.MEMBER.value,
            }

        return MembershipResult(
            status=status,
            is_satisfied=is_satisfied,
        )
