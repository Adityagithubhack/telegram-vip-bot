from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message

from app.bot.routers.menu import send_main_menu
from app.bot.views.membership import send_membership_gate

from app.config.settings import get_settings
from app.services.membership import MembershipService
from app.services.onboarding import OnboardingService
from app.services.referral import ReferralService
from app.services.user import UserService

router = Router(name="start")


@router.message(CommandStart())
async def handle_start(
    message: Message,
    user_service: UserService,
    membership_service: MembershipService,
    onboarding_service: OnboardingService,
    referral_service: ReferralService,
) -> None:
    if message.from_user is None:
        return

    user = await user_service.upsert_from_telegram(message.from_user)

    if message.text:
        parts = message.text.split(maxsplit=1)

        if len(parts) == 2:
            payload = parts[1].strip()

            if payload.startswith("ref_"):
                referral_code = payload.removeprefix("ref_").strip()

                if referral_code:
                    await referral_service.attribute(
                        user_id=user.id,
                        referral_code=referral_code,
                    )

    decision = await membership_service.check_required_channels(
        user=user,
    )

    if not decision.channels:
        progress = await onboarding_service.get_progress(
            user_id=user.id,
        )
        await send_main_menu(
            message,
            progress=progress,
            locale=user.locale,
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

@router.chat_member()
async def handle_channel_member_update(
    event: ChatMemberUpdated,
    user_service: UserService,
    membership_service: MembershipService,
) -> None:
    old_status = str(event.old_chat_member.status)
    new_status = str(event.new_chat_member.status)

    joined_statuses = {"member", "administrator", "creator"}

    # Only react when the user actually becomes a channel member.
    if new_status not in joined_statuses or old_status in joined_statuses:
        return

    telegram_user = event.new_chat_member.user

    if telegram_user.is_bot:
        return

    user = await user_service.get_by_telegram_id(telegram_user.id)
    if user is None:
        return

    # Re-check every required channel. Never grant access from the event alone.
    decision = await membership_service.check_required_channels(user=user)

    if not decision.all_required_joined:
        return

    try:
        await event.bot.send_message(
            chat_id=telegram_user.id,
            text=(
                "✅ <b>JOIN REQUEST ACCEPTED!</b>\n\n"
                "🎉 Your channel access has been approved.\n"
                "🔓 You can now access the bot."
            ),
        )
    except Exception:
        # Telegram may prevent DMs if the user has never started the bot
        # or has blocked it. Membership itself remains unaffected.
        return
