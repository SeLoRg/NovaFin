from common.Core.config import Postgres, Redis
from pydantic_settings import SettingsConfigDict


class Settings(Postgres, Redis):
    REDIS_KEY_IDEMPOTENCY: str
    WALLET_WORKER_REQUEST_TOPIC: str = "wallet.transaction.request"

    STRIPE_PUBLIC_KEY: str
    STRIPE_PRIVATE_KEY: str
    STRIPE_WEBHOOK_SECRET: str

    NOVAFIN_URL: str
    model_config = SettingsConfigDict()


settings = Settings()
