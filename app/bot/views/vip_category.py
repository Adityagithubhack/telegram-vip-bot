from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.services.vip_category import VipCategoryItem

CATEGORY_LABELS = {
    "standard": "⭐ STANDARD VIP",
    "premium": "💎 PREMIUM VIP",
    "elite": "👑 ELITE VIP",
}


def build_vip_category_keyboard(
    categories: list[VipCategoryItem],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for category in categories:
        label = CATEGORY_LABELS.get(
            category.code,
            category.code.replace("_", " ").upper(),
        )

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
) -> None:
    await message.answer(
        "💎 <b>SELECT YOUR VIP CATEGORY</b>\n\n"
        "Choose the VIP category you want to explore:",
        reply_markup=build_vip_category_keyboard(categories),
    )
