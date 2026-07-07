from __future__ import annotations

from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

_pool = ConnectionPool.from_url(settings.REDIS_DSN, decode_responses=True)


def get_redis() -> Redis:
    """Returns a Redis client backed by a shared connection pool.

    Cheap to call repeatedly -- Redis() with a pool does not open a new
    connection, it borrows one from the pool.
    """
    return Redis(connection_pool=_pool)
