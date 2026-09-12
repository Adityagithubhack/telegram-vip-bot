from enum import StrEnum
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class BotMode(StrEnum):
    POLLING = "polling"
    WEBHOOK = "webhook"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"

    bot_token: SecretStr
    bot_mode: BotMode = BotMode.POLLING

    webhook_base_url: str | None = None
    webhook_path: str = "/telegram/webhook"
    webhook_secret: SecretStr | None = None

    database_url: str
    redis_url: str

    super_admin_telegram_id: int | None = None

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.PRODUCTION

    def validate_runtime(self) -> None:
        if self.bot_mode is BotMode.WEBHOOK:
            if not self.webhook_base_url:
                raise ValueError(
                    "WEBHOOK_BASE_URL is required when BOT_MODE=webhook"
                )

            if self.webhook_secret is None:
                raise ValueError(
                    "WEBHOOK_SECRET is required when BOT_MODE=webhook"
                )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime()
    return settings
