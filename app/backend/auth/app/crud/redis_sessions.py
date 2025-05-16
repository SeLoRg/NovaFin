import redis
from auth.Core.config import settings
from auth.Core.redis_client import redis_client
from datetime import datetime, timedelta, timezone


class RedisSessions:
    def __init__(self, redis_cli: redis.Redis, session_prefix: str):
        self.redis_cli = redis_cli
        self.session_prefix = session_prefix

    async def add_refresh_token(self, user_id: str, refresh_token: str):
        sessions_key = f"sessions:{user_id}"
        current_time = datetime.timestamp(datetime.now(tz=timezone.utc))
        await self.redis_cli.zadd(sessions_key, {refresh_token: current_time})

        if await self.redis_cli.zcard(sessions_key) > settings.MAX_SESSIONS:
            await self.redis_cli.zremrangebyrank(sessions_key, 0, 0)

        await self.redis_cli.expire(sessions_key, settings.REDIS_SESSIONS_LIVE)

    def get_refresh_tokens(self, user_id: str) -> list[str]:
        sessions_key = f"sessions:{user_id}"
        return self.redis_cli.zrange(sessions_key, 0, -1)

    async def is_token_expired(self, user_id: str, refresh_token: str) -> bool:
        score = await self.redis_cli.zscore(f"sessions:{user_id}", refresh_token)

        if score is None:
            return True

        return score < int(datetime.now(tz=timezone.utc).timestamp())

    async def remove_expired_tokens(self, user_id: str):
        await self.redis_cli.zremrangebyscore(
            f"sessions:{user_id}",
            "-inf",
            int(datetime.now(tz=timezone.utc).timestamp()),
        )

    async def remove_token(self, user_id: str, refresh_token: str):
        """
        :param refresh_token: id refresh токена
        """
        await self.redis_cli.zrem(f"sessions:{user_id}", refresh_token)


redis_sessions_helper = RedisSessions(
    redis_cli=redis_client, session_prefix=settings.REDIS_KEY_SESSIONS
)
