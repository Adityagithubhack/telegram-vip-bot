from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.middlewares.admin import AdminRequiredMiddleware
from app.bot.middlewares.membership import MembershipRequiredMiddleware
from app.bot.routers.admin import router as admin_router
from app.bot.routers.menu import router as menu_router
from app.bot.routers.start import router as start_router
from app.gateways.telegram_membership import TelegramMembershipGateway
from app.services.admin import AdminService
from app.services.admin_vip import AdminVipService
from app.services.audit_log import AuditLogService
from app.services.channel_settings import ChannelSettingsService
from app.services.content_screen_settings import ContentScreenSettingsService
from app.services.daily_pick import DailyPickService
from app.services.live_stats import LiveStatsService
from app.services.membership import MembershipService
from app.services.notification_preference import NotificationPreferenceService
from app.services.referral import ReferralService
from app.services.onboarding import OnboardingService
from app.services.user import UserService
from app.services.vip_category import VipCategoryService
from app.services.vip_menu_settings import VipMenuSettingsService


def create_dispatcher(
    *,
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
) -> Dispatcher:
    dispatcher = Dispatcher(
        storage=MemoryStorage(),
        user_service=UserService(session_factory),
        membership_service=MembershipService(
            session_factory=session_factory,
            gateway=TelegramMembershipGateway(bot),
        ),
        onboarding_service=OnboardingService(session_factory),
        vip_category_service=VipCategoryService(session_factory),
        vip_menu_settings_service=VipMenuSettingsService(session_factory),
        content_screen_settings_service=ContentScreenSettingsService(session_factory),
        live_stats_service=LiveStatsService(session_factory),
        referral_service=ReferralService(session_factory),
        notification_preference_service=NotificationPreferenceService(session_factory),
        audit_log_service=AuditLogService(session_factory),
        channel_settings_service=ChannelSettingsService(session_factory),
        admin_service=AdminService(session_factory),
        admin_vip_service=AdminVipService(session_factory),
        daily_pick_service=DailyPickService(session_factory),
    )

    admin_router.message.middleware(
        AdminRequiredMiddleware()
    )
    admin_router.callback_query.middleware(
        AdminRequiredMiddleware()
    )

    menu_router.message.outer_middleware(
        MembershipRequiredMiddleware()
    )
    menu_router.callback_query.outer_middleware(
        MembershipRequiredMiddleware()
    )

    dispatcher.include_router(start_router)
    dispatcher.include_router(admin_router)
    dispatcher.include_router(menu_router)

    return dispatcher
