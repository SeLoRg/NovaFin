from __future__ import annotations

from redis import Redis
from wallet_service.Core.config import settings


class IdempotencyCache:
    """Thin wrapper around Redis for idempotency keys."""

    def __init__(self, redis: Redis):
        self._redis = redis

    async def exists(self, key: str) -> bool:
        return bool(await self._redis.exists(f"{settings.REDIS_KEY_IDEMPOTENCY}:{key}"))

    async def remember(self, key: str, ttl: int = 24 * 3600) -> None:
        await self._redis.setex(
            name=f"{settings.REDIS_KEY_IDEMPOTENCY}:{key}", value="", time=ttl
        )
