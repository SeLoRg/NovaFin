from pydantic_settings import SettingsConfigDict, BaseSettings
from common.Core.config import Google, PaymentStripe


class Settings(Google, PaymentStripe):
    JWT_ACCESS_COOKIE: str = "access-token"
    JWT_REFRESH_COOKIE: str = "refresh-token"

    ACCESS_MAX_AGE_COOKIE_S: int = 604800
    REFRESH_MAX_AGE_COOKIE_S: int = 604800

    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()
