from pydantic_settings import SettingsConfigDict
from common.Core.config import Postgres


class Settings(Postgres):
    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()
