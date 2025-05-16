from pydantic_settings import SettingsConfigDict
import os
from common.Core.config import Postgres, Redis, SMTPMail


class Settings(SMTPMail):
    model_config = SettingsConfigDict()


settings = Settings()
