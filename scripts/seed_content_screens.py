import asyncio

from sqlalchemy import select

from app.config.settings import get_settings
from app.infra.db.session import create_session_factory
from app.infra.db.models.content_screen_settings import ContentScreenSettings


SCREENS = [
    ("winning_tips", "🎯 DAILY WINNING TIPS"),
    ("today_insights", "🔥 TODAY'S SPORTS INTELLIGENCE"),
    ("live_stats", "🏆 LIVE COMMUNITY STATS"),
    ("referral", "🎁 REFER & EARN"),
    ("how_it_works", "📖 HOW IT WORKS"),
    ("notifications", "🔔 NOTIFICATIONS"),
    ("support", "💬 VIP SUPPORT"),
]


async def main() -> None:
    settings = get_settings()
    session_factory = create_session_factory(settings)

    async with session_factory() as session:
        for screen_key, heading in SCREENS:
            result = await session.execute(
                select(ContentScreenSettings).where(
                    ContentScreenSettings.screen_key == screen_key
                )
            )
            existing = result.scalar_one_or_none()

            if existing is None:
                session.add(
                    ContentScreenSettings(
                        screen_key=screen_key,
                        heading=heading,
                        is_active=True,
                    )
                )

        await session.commit()

    print("Content screens seeded.")


if __name__ == "__main__":
    asyncio.run(main())
