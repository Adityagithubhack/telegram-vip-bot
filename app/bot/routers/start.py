from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.services.membership import MembershipDecision, MembershipService
from app.services.user import UserService

router = Router(name="start")


def build_membership_keyboard(
    decision: MembershipDecision,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for channel in decision.channels:
        if channel.is_satisfied:
            continue

        url = channel.invite_url
        if url is None and channel.username is not None:
            url = f"https://t.me/{channel.username}"

        if url is not None:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"📢 JOIN {channel.title}",
                        url=url,
                    )
                ]
            )

    rows.append(
        [
            InlineKeyboardButton(
                text="✅ I'VE JOINED",
                callback_data="membership:verify",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_membership_gate(
    message: Message,
    decision: MembershipDecision,
) -> None:
    lines = [
        "🏆 <b>SPIDY’S ADMIN</b>",
        "",
        "🔒 <b>ONE STEP BEFORE YOUR ACCESS</b>",
        "",
        "Please join the required channel first.",
        "",
    ]

    for channel in decision.channels:
        icon = "✅" if channel.is_satisfied else "❌"
        lines.append(f"{icon} {channel.title}")

    lines.extend(
        [
            "",
            "After joining, tap <b>✅ I'VE JOINED</b>.",
        ]
    )

    await message.answer(
        "\n".join(lines),
        reply_markup=build_membership_keyboard(decision),
    )


@router.message(CommandStart())
async def handle_start(
    message: Message,
    user_service: UserService,
    membership_service: MembershipService,
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
        await message.answer(
            "✅ <b>Membership verified</b>\n\n"
            "Welcome to SPIDY’S ADMIN.\n"
            "Your access is active."
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
                "✅ <b>Membership verified</b>\n\n"
                "Welcome to SPIDY’S ADMIN.\n"
                "Your access is active."
            )
        return

    await callback.answer(
        "❌ Not joined yet — join the channel first",
        show_alert=True,
    )
