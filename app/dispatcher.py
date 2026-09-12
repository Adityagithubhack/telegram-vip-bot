from aiogram import Bot, Dispatcher
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.routers.start import router as start_router
from app.gateways.telegram_membership import TelegramMembershipGateway
from app.services.membership import MembershipService
from app.services.user import UserService


def create_dispatcher(
    *,
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
) -> Dispatcher:
    dispatcher = Dispatcher(
        user_service=UserService(session_factory),
        membership_service=MembershipService(
            session_factory=session_factory,
            gateway=TelegramMembershipGateway(bot),
        ),
    )

    dispatcher.include_router(start_router)

    return dispatcher
