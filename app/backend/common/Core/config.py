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


class PaymentStripe(BaseSettings):
    STRIPE_PUBLIC_KEY: str
    STRIPE_PRIVATE_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    STRIPE_WEBHOOK_PAYOUT_SECRET: str

    model_config = SettingsConfigDict(extra="ignore")


class Google(BaseSettings):
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_TOKEN_URL: str
    GOOGLE_USERINFO_URL: str

    @property
    def GOOGLE_OAUTH_REDIRECT_URI(self):
        return f"{self.NOVAFIN_URL}/api/auth/google/callback"

    model_config = SettingsConfigDict(extra="ignore")
