from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name="start")


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer(
        "👋 <b>Welcome to SPIDY’S ADMIN</b>\n\n"
        "Bot foundation is working successfully.\n"
        "Next, we will build the real onboarding and membership gate."
    )
