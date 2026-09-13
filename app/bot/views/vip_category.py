from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.services.vip_category import VipCategoryItem
from app.services.vip_menu_settings import VipMenuSettingsItem


def build_vip_category_keyboard(
    categories: list[VipCategoryItem],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for category in categories:
        label = category.display_name

        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"vip_category:{category.id}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🏠 MAIN MENU",
                callback_data="menu:home",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_vip_categories(
    message: Message,
    *,
    categories: list[VipCategoryItem],
    settings: VipMenuSettingsItem | None,
) -> None:
    heading = (
        escape(settings.heading)
        if settings
        else "WHICH VIP EXPERIENCE INTERESTS YOU MOST?"
    )

    description = (
        escape(settings.description)
        if settings and settings.description
        else "Explore the available VIP experiences."
    )

    footer_text = (
        escape(settings.footer_text)
        if settings
        else "Tap any option below 👇"
    )

    category_names = "\n".join(
        f"• {escape(category.display_name)}"
        for category in categories
    )

    await message.answer(
        f"💎 <b>{heading}</b>\n\n"
        f"{description}\n\n"
        f"<b>AVAILABLE VIP OPTIONS</b>\n"
        f"{category_names}\n\n"
        f"{footer_text}",
        reply_markup=build_vip_category_keyboard(categories),
    )


def build_vip_detail_keyboard(
    *,
    category: VipCategoryItem,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if category.registration_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🔗 REGISTER NOW",
                    url=category.registration_url,
                )
            ]
        )

    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text="✅ SELECT THIS VIP",
                    callback_data=f"vip_category_select:{category.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚀 GET VIP ACCESS",
                    callback_data=f"vip_category_select:{category.id}",
                )
            ],
        ]
    )

    if category.support_username:
        rows.append(
            [
                InlineKeyboardButton(
                    text="💬 VIP SUPPORT",
                    url=f"https://t.me/{category.support_username}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="💎 VIP OPTIONS",
                callback_data="menu:vip_options",
            )
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="🏠 MAIN MENU",
                callback_data="menu:home",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_vip_category_detail(
    message: Message,
    *,
    category: VipCategoryItem,
) -> None:
    title = escape(category.display_name)

    if category.media_file_id:
        if category.media_type == "photo":
            await message.answer_photo(
                photo=category.media_file_id,
            )
        else:
            await message.answer_video(
                video=category.media_file_id,
            )

    promo_code = (
        escape(category.promo_code)
        if category.promo_code
        else "Not configured yet"
    )

    vip_info = (
        escape(category.vip_info)
        if category.vip_info
        else "VIP information will be available here soon."
    )

    registration_status = (
        "Tap <b>REGISTER NOW</b> below to open the official registration link."
        if category.registration_url
        else "Registration link will be available here soon."
    )

    support_contact = (
        f"@{escape(category.support_username)}"
        if category.support_username
        else "VIP Support"
    )

    await message.answer(
        f"👑 <b>{title}</b>\n\n"
        f"{vip_info}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🏆 <b>HOW VIP ACCESS WORKS</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "1️⃣ Choose this VIP category.\n\n"
        f"2️⃣ {registration_status}\n\n"
        f"3️⃣ Promo Code: <code>{promo_code}</code>\n\n"
        f"4️⃣ Support: {support_contact}\n\n"
        "After registration, send the required details to support:\n"
        "• Player / User ID\n"
        "• Registration details\n"
        f"• Selected VIP: <b>{title}</b>\n\n"
        "5️⃣ Wait for admin verification.\n\n"
        "✅ VIP access is activated only after admin approval.",
        reply_markup=build_vip_detail_keyboard(
            category=category,
        ),
    )
