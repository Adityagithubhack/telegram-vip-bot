from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.bot.views.membership import send_membership_gate
from app.services.membership import MembershipService
from app.services.user import UserService


class MembershipRequiredMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[
            [TelegramObject, dict[str, Any]],
            Awaitable[Any],
        ],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_service: UserService = data["user_service"]
        membership_service: MembershipService = data[
            "membership_service"
        ]

        if isinstance(event, Message):
            telegram_user = event.from_user
            message = event
        elif isinstance(event, CallbackQuery):
            telegram_user = event.from_user

            if not isinstance(event.message, Message):
                return None

            message = event.message
        else:
            return await handler(event, data)

        if telegram_user is None:
            return None

        user = await user_service.upsert_from_telegram(
            telegram_user
        )

        decision = await membership_service.check_required_channels(
            user=user,
        )

        if decision.all_required_joined:
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            await event.answer(
                "❌ Join the required channel first",
                show_alert=True,
            )

        await send_membership_gate(
            message,
            decision,
        )

        return None
