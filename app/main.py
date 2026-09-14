import asyncio

import structlog
from aiogram.types import BotCommand

from app.bot.factory import create_bot
from app.config.settings import BotMode, get_settings
from app.core.logging import configure_logging
from app.dispatcher import create_dispatcher
from app.infra.db.session import create_session_factory
from app.services.admin import AdminService


async def run_polling() -> None:
    settings = get_settings()

    bot = create_bot(settings.bot_token.get_secret_value())
    session_factory = create_session_factory(settings)

    if settings.super_admin_telegram_id is not None:
        admin_service = AdminService(session_factory)
        await admin_service.ensure_owner(
            settings.super_admin_telegram_id
        )
    dispatcher = create_dispatcher(
        bot=bot,
        session_factory=session_factory,
    )

    log = structlog.get_logger(__name__)

    try:
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Start your premium experience"),
                BotCommand(command="menu", description="Open the main menu"),
                BotCommand(command="vip", description="Explore VIP options"),
                BotCommand(command="myvip", description="Open your VIP dashboard"),
                BotCommand(command="dailypicks", description="View today's VIP picks"),
                BotCommand(command="compare", description="Compare VIP options"),
                BotCommand(command="howitworks", description="See how VIP access works"),
                BotCommand(command="language", description="Change your language"),
                BotCommand(command="support", description="Contact VIP support"),
            ]
        )

        bot_info = await bot.get_me()

        log.info(
            "bot_starting",
            mode=settings.bot_mode.value,
            bot_id=bot_info.id,
            bot_username=bot_info.username,
        )

        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
    finally:
        await bot.session.close()
        log.info("bot_stopped")


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    if settings.bot_mode is BotMode.POLLING:
        await run_polling()
        return

    raise RuntimeError("Webhook mode is not implemented yet")


if __name__ == "__main__":
    asyncio.run(main())
