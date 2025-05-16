from pydantic_settings import SettingsConfigDict, BaseSettings


class Settings(BaseSettings):
    JWT_ACCESS_COOKIE: str = "access-token"
    JWT_REFRESH_COOKIE: str = "refresh-token"

    ACCESS_MAX_AGE_COOKIE_S: int = 604800
    REFRESH_MAX_AGE_COOKIE_S: int = 604800
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_OAUTH_REDIRECT_URI: str
    model_config = SettingsConfigDict()


settings = Settings()
