from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central, strictly-typed application configuration.

    All values are loaded from environment / .env. Nothing bot-specific
    lives here -- per-bot data (token, branding, captcha, menu, ...) lives
    in the database and is loaded dynamically at runtime.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    ENV: str = "production"
    LOG_LEVEL: str = "INFO"
    BASE_WEBHOOK_URL: str = Field(..., description="Public base URL, e.g. https://bots.example.com")
    WEBHOOK_SECRET: str = Field(..., description="Secret token validated on every incoming webhook request")
    WEB_SERVER_HOST: str = "0.0.0.0"
    WEB_SERVER_PORT: int = 8080

    # --- Admin ---
    ADMIN_TG_ID: int = Field(..., description="Single Telegram user id allowed to control the Admin bot")
    ADMIN_BOT_TOKEN: str = Field(..., description="Token of the master admin bot")

    # --- Database ---
    POSTGRES_DSN: str = Field(..., description="postgresql+asyncpg://user:pass@host:5432/dbname")
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # --- Redis ---
    REDIS_DSN: str = Field("redis://redis:6379/0")

    # --- Rate limiting / throttling ---
    SUBSCRIPTION_CHECK_CACHE_TTL: int = 30  # seconds, avoid hammering getChatMember
    BROADCAST_MESSAGES_PER_SECOND: int = 25  # stay under Telegram's ~30/s global limit

    @property
    def webhook_secret_header(self) -> str:
        return "X-Telegram-Bot-Api-Secret-Token"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
