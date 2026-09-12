from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config.settings import get_settings
from app.services.admin_vip import AdminVipService
from app.services.onboarding import OnboardingService
from app.services.user import UserService

router = Router(name="admin")


def _is_super_admin(telegram_user_id: int) -> bool:
    settings = get_settings()

    return (
        settings.super_admin_telegram_id is not None
        and telegram_user_id == settings.super_admin_telegram_id
    )


def _admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏳ PENDING VIP APPROVALS",
                    callback_data="admin:vip_pending",
                )
            ]
        ]
    )


@router.message(Command("admin"))
async def handle_admin(message: Message) -> None:
    if message.from_user is None:
        return

    if not _is_super_admin(message.from_user.id):
        await message.answer("⛔ You are not authorized.")
        return

    await message.answer(
        "🛡 <b>ADMIN PANEL</b>\n\n"
        "✅ Super admin access verified.",
        reply_markup=_admin_keyboard(),
    )


@router.callback_query(F.data == "admin:vip_pending")
async def handle_pending_vip_approvals(
    callback: CallbackQuery,
    onboarding_service: OnboardingService,
    user_service: UserService,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    pending = await onboarding_service.list_pending_vip_approvals()

    if not pending:
        await callback.answer()
        if isinstance(callback.message, Message):
            await callback.message.answer(
                "✅ No pending VIP approvals."
            )
        return

    users = await user_service.get_by_ids(
        [item.user_id for item in pending]
    )

    users_by_id = {
        user.id: user
        for user in users
    }

    lines = [
        "⏳ <b>PENDING VIP APPROVALS</b>",
        "",
    ]

    keyboard_rows: list[list[InlineKeyboardButton]] = []

    for item in pending:
        user = users_by_id.get(item.user_id)

        if user is None:
            continue

        display_name = (
            user.first_name
            or user.username
            or str(user.telegram_user_id)
        )

        username = (
            f"@{user.username}"
            if user.username
            else "No username"
        )

        lines.append(
            f"👤 <b>{display_name}</b>\n"
            f"ID: <code>{user.telegram_user_id}</code>\n"
            f"{username}"
        )
        lines.append("")

        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text=f"✅ Approve {display_name}",
                    callback_data=f"admin:vip_approve:{user.id}",
                )
            ]
        )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=keyboard_rows
            ),
        )

    await callback.answer()

@router.callback_query(F.data.startswith("admin:vip_approve:"))
async def handle_vip_approve(
    callback: CallbackQuery,
    admin_vip_service: AdminVipService,
    bot: Bot,
) -> None:
    if not _is_super_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Unauthorized",
            show_alert=True,
        )
        return

    if callback.data is None:
        return

    try:
        user_id = int(
            callback.data.removeprefix(
                "admin:vip_approve:"
            )
        )
    except ValueError:
        await callback.answer(
            "Invalid approval request",
            show_alert=True,
        )
        return

    result = await admin_vip_service.approve_vip(
        actor_telegram_user_id=callback.from_user.id,
        user_id=user_id,
    )

    if not result.granted:
        messages = {
            "onboarding_not_found": "❌ User onboarding not found",
            "already_granted": "ℹ️ VIP access already granted",
            "contact_not_verified": "❌ Contact verification is incomplete",
        }

        await callback.answer(
            messages.get(
                result.reason,
                "❌ VIP approval failed",
            ),
            show_alert=True,
        )
        return

    if result.telegram_user_id is not None:
        await bot.send_message(
            chat_id=result.telegram_user_id,
            text=(
                "👑 <b>VIP ACCESS GRANTED</b>\n\n"
                "Your VIP access has been approved successfully.\n"
                "Open your dashboard to continue."
            ),
        )

    await callback.answer(
        "✅ VIP access granted",
        show_alert=True,
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            "👑 <b>VIP ACCESS GRANTED</b>\n\n"
            f"Internal user ID: <code>{user_id}</code>"
        )
