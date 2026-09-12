import asyncio

import structlog

from app.bot.factory import create_bot
from app.config.settings import BotMode, get_settings
from app.core.logging import configure_logging
from app.dispatcher import create_dispatcher


async def run_polling() -> None:
    settings = get_settings()

    bot = create_bot(settings.bot_token.get_secret_value())
    dispatcher = create_dispatcher()

    log = structlog.get_logger(__name__)

    try:
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
