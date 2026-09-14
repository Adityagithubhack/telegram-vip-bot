from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.services.admin import AdminService


class AdminRequiredMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler: Callable[
            [TelegramObject, dict[str, Any]],
            Awaitable[Any],
        ],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        admin_service: AdminService = data["admin_service"]

        if isinstance(event, Message):
            telegram_user = event.from_user
        elif isinstance(event, CallbackQuery):
            telegram_user = event.from_user
        else:
            return await handler(event, data)

        if telegram_user is None:
            return None

        if await admin_service.is_admin(telegram_user.id):
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            await event.answer(
                "⛔ Unauthorized",
                show_alert=True,
            )
        elif isinstance(event, Message):
            await event.answer(
                "⛔ You are not authorized."
            )

        return None
