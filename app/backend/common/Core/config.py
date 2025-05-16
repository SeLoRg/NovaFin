from pydantic_settings import BaseSettings, SettingsConfigDict


class Postgres(BaseSettings):
    POSTGRES_PASSWORD: str
    POSTGRES_USER: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str

    @property
    def postgres_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict()


class Redis(BaseSettings):
    REDIS_HOST: str
    REDIS_PORT: str
    REDIS_DB: str

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = SettingsConfigDict()


class SMTPMail(BaseSettings):
    SMTP_MAIL_SERVER: str
    SMTP_MAIL_PORT: str
    SMTP_MAIL_USER: str
    SMTP_MAIL_PASSWORD: str
    SMTP_MAIL_FROM: str
    SMTP_MAIL_FROM_NAME: str
    SMTP_MAIL_STARTTLS: str
    SMTP_MAIL_SSL_TLS: str

    model_config = SettingsConfigDict()
