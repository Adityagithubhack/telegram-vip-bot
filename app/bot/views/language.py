from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message


def build_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🇬🇧 English",
                    callback_data="language:en",
                ),
                InlineKeyboardButton(
                    text="🇮🇳 Hindi",
                    callback_data="language:hi",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🇧🇩 Bengali",
                    callback_data="language:bn",
                ),
                InlineKeyboardButton(
                    text="🇳🇵 Nepali",
                    callback_data="language:ne",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏠 MAIN MENU",
                    callback_data="menu:home",
                )
            ],
        ]
    )


async def send_language_menu(message: Message) -> None:
    await message.answer(
        "🌐 <b>SELECT YOUR LANGUAGE</b>\n\n"
        "Choose your preferred language below:",
        reply_markup=build_language_keyboard(),
    )
