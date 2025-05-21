from common.Core.config import Postgres, Redis, PaymentStripe
from pydantic_settings import SettingsConfigDict


class Settings(Postgres, Redis, PaymentStripe):
    REDIS_KEY_IDEMPOTENCY: str
    WALLET_WORKER_REQUEST_TOPIC: str = "wallet.transaction.request"
    PAYMENT_TEST_MODE: bool = True
    NOVAFIN_URL: str

    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()
