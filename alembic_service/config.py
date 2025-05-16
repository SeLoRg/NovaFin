from pydantic_settings import SettingsConfigDict

from app.backend.common.Core.config import Postgres


class Settings(Postgres):
    model_config = SettingsConfigDict()


settings = Settings()
