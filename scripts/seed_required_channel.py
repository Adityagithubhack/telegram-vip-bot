import asyncio

from aiogram import Bot
from sqlalchemy import select

from app.config.settings import get_settings
from app.infra.db.models.channel import Channel
from app.infra.db.session import create_session_factory


async def main() -> None:
    settings = get_settings()

    if not settings.required_channel_username:
        print("No required channel configured. Skipping.")
        return

    bot = Bot(settings.bot_token.get_secret_value())
    session_factory = create_session_factory(settings)

    try:
        chat = await bot.get_chat(
            f"@{settings.required_channel_username.lstrip('@')}"
        )

        invite_url = settings.required_channel_invite_url
        if not invite_url and chat.username:
            invite_url = f"https://t.me/{chat.username}"

        async with session_factory() as session:
            result = await session.execute(
                select(Channel).where(
                    Channel.telegram_chat_id == chat.id
                )
            )
            existing = result.scalar_one_or_none()

            if existing is None:
                session.add(
                    Channel(
                        telegram_chat_id=chat.id,
                        title=chat.title or chat.username or str(chat.id),
                        username=chat.username,
                        invite_url=invite_url,
                        is_required=True,
                        is_active=True,
                        priority=100,
                    )
                )
                print("Required channel created.")
            else:
                existing.title = (
                    chat.title
                    or chat.username
                    or str(chat.id)
                )
                existing.username = chat.username
                existing.invite_url = invite_url
                existing.is_required = True
                existing.is_active = True
                existing.priority = 100
                print("Required channel updated.")

            await session.commit()

    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
