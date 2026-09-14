from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.services.membership import MembershipDecision

from app.config.settings import get_settings


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

    return InlineKeyboardMarkup(
        inline_keyboard=rows,
    )


async def send_membership_gate(
    message: Message,
    decision: MembershipDecision,
) -> None:
    lines = [
        f"🏆 <b>{get_settings().admin_brand_name}</b>",
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
