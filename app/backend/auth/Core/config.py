from pydantic_settings import SettingsConfigDict
import os
from common.Core.config import Postgres, Redis
from pathlib import Path


class Settings(Postgres, Redis):
    jwt_private_key: Path = Path("auth/certs/jwt_private.pem")
    jwt_public_key: Path = Path("auth/certs/jwt_public.pem")

    jwt_access_live_m: float = 15.0
    jwt_refresh_live_m: float = 10080.0
    jwt_algorithm: str = "RS256"

    REDIS_KEY_SESSIONS: str
    MAX_SESSIONS: int
    REDIS_SESSIONS_LIVE: int
    REDIS_KEY_OPT: str

    GOOGLE_CLIENT_ID: str
    GOOGLE_OAUTH_REDIRECT_URI: str
    GOOGLE_CLIENT_SECRET: str
    # GOOGLE_AUTH_URL: str
    GOOGLE_TOKEN_URL: str
    GOOGLE_USERINFO_URL: str

    model_config = SettingsConfigDict()


settings = Settings()
