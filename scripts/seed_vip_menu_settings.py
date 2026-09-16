import asyncio

from sqlalchemy import select

from app.config.settings import get_settings
from app.infra.db.session import create_session_factory
from app.infra.db.models.vip_menu_settings import VipMenuSettings


async def main() -> None:
    settings = get_settings()
    session_factory = create_session_factory(settings)

    async with session_factory() as session:
        result = await session.execute(
            select(VipMenuSettings).order_by(VipMenuSettings.id.asc()).limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            session.add(VipMenuSettings())
            await session.commit()
            print("VIP menu settings seeded.")
        else:
            print("VIP menu settings already exist. No changes made.")


if __name__ == "__main__":
    asyncio.run(main())
