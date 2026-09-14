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
                InlineKeyboardButton(text="🇪🇸 Spanish", callback_data="language:es"),
                InlineKeyboardButton(text="🇫🇷 French", callback_data="language:fr"),
            ],
            [
                InlineKeyboardButton(text="🇩🇪 German", callback_data="language:de"),
                InlineKeyboardButton(text="🇵🇹 Portuguese", callback_data="language:pt"),
            ],
            [
                InlineKeyboardButton(text="🇮🇹 Italian", callback_data="language:it"),
                InlineKeyboardButton(text="🇷🇺 Russian", callback_data="language:ru"),
            ],
            [
                InlineKeyboardButton(text="🇸🇦 Arabic", callback_data="language:ar"),
                InlineKeyboardButton(text="🇹🇷 Turkish", callback_data="language:tr"),
            ],
            [
                InlineKeyboardButton(text="🇮🇩 Indonesian", callback_data="language:id"),
                InlineKeyboardButton(text="🇯🇵 Japanese", callback_data="language:ja"),
            ],
            [
                InlineKeyboardButton(text="🇰🇷 Korean", callback_data="language:ko"),
                InlineKeyboardButton(text="🇨🇳 Chinese", callback_data="language:zh"),
            ],
            [
                InlineKeyboardButton(text="🇳🇱 Dutch", callback_data="language:nl"),
                InlineKeyboardButton(text="🇵🇱 Polish", callback_data="language:pl"),
            ],
            [
                InlineKeyboardButton(text="🇻🇳 Vietnamese", callback_data="language:vi"),
                InlineKeyboardButton(text="🇹🇭 Thai", callback_data="language:th"),
            ],
            [
                InlineKeyboardButton(text="🇮🇷 Persian", callback_data="language:fa"),
                InlineKeyboardButton(text="🇺🇦 Ukrainian", callback_data="language:uk"),
            ],
            [
                InlineKeyboardButton(text="🇲🇾 Malay", callback_data="language:ms"),
                InlineKeyboardButton(text="🇵🇭 Filipino", callback_data="language:fil"),
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
