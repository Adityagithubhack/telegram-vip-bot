from aiogram import Dispatcher

from app.bot.routers.start import router as start_router


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()

    dispatcher.include_router(start_router)

    return dispatcher
