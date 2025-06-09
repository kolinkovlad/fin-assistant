from functools import lru_cache

from redis.asyncio import Redis

from app.settings import get_settings


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(str(get_settings().REDIS_URL), decode_responses=True)