from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

_pool: ConnectionPool | None = None


async def get_redis() -> Redis:
    global _pool
    if _pool is None:
        # socket_timeout must exceed BLOCK_MS (5s) used by XREADGROUP BLOCK.
        # redis-py 8.x defaults to 5s which races with the block timeout;
        # from_url ignores socket_timeout=None, so we set an explicit 30s.
        _pool = ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=30,
            socket_connect_timeout=5,
        )
    return Redis(connection_pool=_pool)


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
