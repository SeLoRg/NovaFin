from redis.asyncio import Redis, ConnectionPool
from wallet_service.Core.config import settings


connection_pool = ConnectionPool(
    host=settings.REDIS_HOST,
    port=int(settings.REDIS_PORT),
    db=int(settings.REDIS_DB),
)

async_redis_client: Redis = Redis(
    connection_pool=connection_pool,
    decode_responses=True,
)
