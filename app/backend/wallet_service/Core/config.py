from common.Core.config import Postgres, Redis
from pydantic_settings import SettingsConfigDict


class Settings(Postgres, Redis):
    REDIS_KEY_IDEMPOTENCY: str
    WALLET_WORKER_REQUEST_TOPIC: str = "wallet.transaction.request"

    model_config = SettingsConfigDict()


settings = Settings()
