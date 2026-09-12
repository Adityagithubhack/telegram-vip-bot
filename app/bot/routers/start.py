from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from app.bot.routers.menu import send_main_menu
from app.bot.views.membership import send_membership_gate
from app.services.membership import MembershipService
from app.services.onboarding import OnboardingService
from app.services.user import UserService

router = Router(name="start")


@router.message(CommandStart())
async def handle_start(
    message: Message,
    user_service: UserService,
    membership_service: MembershipService,
    onboarding_service: OnboardingService,
) -> None:
    if message.from_user is None:
        return

    user = await user_service.upsert_from_telegram(message.from_user)

    decision = await membership_service.check_required_channels(
        user=user,
    )

    if not decision.channels:
        await message.answer(
            "👋 <b>Welcome to SPIDY’S ADMIN</b>\n\n"
            "No required channels are configured yet."
        )
        return

    if decision.all_required_joined:
        progress = await onboarding_service.get_progress(
            user_id=user.id,
        )
        await send_main_menu(
            message,
            progress=progress,
        )
        return

    await send_membership_gate(
        message,
        decision,
    )


@router.callback_query(F.data == "membership:verify")
async def handle_membership_verify(
    callback: CallbackQuery,
    user_service: UserService,
    membership_service: MembershipService,
    onboarding_service: OnboardingService,
) -> None:
    if callback.from_user is None:
        return

    user = await user_service.upsert_from_telegram(
        callback.from_user
    )

    decision = await membership_service.check_required_channels(
        user=user,
    )

    if decision.all_required_joined:
        await callback.answer(
            "✅ Membership verified",
            show_alert=False,
        )

        if isinstance(callback.message, Message):
            await callback.message.edit_text(
                "✅ <b>Membership verified</b>"
            )
            progress = await onboarding_service.get_progress(
                user_id=user.id,
            )
            await send_main_menu(
                callback.message,
                progress=progress,
            )
        return

    await callback.answer(
        "❌ Not joined yet — join the channel first",
        show_alert=True,
    )

@router.message(Command("id"))
async def handle_id(message: Message) -> None:
    if message.from_user is None:
        return

    await message.answer(
        f"Your Telegram ID: <code>{message.from_user.id}</code>"
    )
