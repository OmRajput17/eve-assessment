from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """All configuration comes from environment variables (12-factor style)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/eve"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    webhook_secret: str = "change-me-webhook-secret"

    payment_success_rate: float = 0.8
    allow_payment_override: bool = True

    admin_emails: list[str] = []

@lru_cache
def get_settings() -> Settings:
    return Settings()
