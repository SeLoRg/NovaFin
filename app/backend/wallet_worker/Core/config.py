from common.Core.config import Postgres, Redis
from pydantic_settings import SettingsConfigDict


class Settings(Postgres, Redis):
    KAFKA_BROKER: str = "kafka:9092"
    INPUT_TOPIC: str = "wallet.transaction.request"
    OUTPUT_TOPIC: str = "wallet.transaction.result"
    REDIS_KEY_IDEMPOTENCY: str

    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()
