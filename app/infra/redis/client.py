from typing import cast

from redis.asyncio import Redis

from app.config.settings import Settings


def create_redis_client(settings: Settings) -> Redis:
    client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
    return cast(Redis, client)
