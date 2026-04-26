"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = Field(
        default="development",
        description="The environment the application is running in.",
    )

    # OpenAI
    openai_api_key: str = Field(
        default="sk-placeholder",
        description="OpenAI API key for AI agents.",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="Default OpenAI model to use for AI agents.",
    )

    # Database
    database_url: str = Field(
        default=(
            "mysql+aiomysql://helios:helios_dev@localhost:3306/helios"  # pragma: allowlist secret
        ),
        description="Async database URL for application use.",
    )
    database_url_sync: str = Field(
        default=(
            "mysql+pymysql://helios:helios_dev@localhost:3306/helios"  # pragma: allowlist secret
        ),
        description="Sync database URL for migrations and seeding.",
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL.",
    )

    # API
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    api_host: str = Field(default="0.0.0.0")  # noqa: S104
    api_port: int = Field(default=8000)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance.

    Cached so the .env file is only read once per process.
    Also exports OPENAI_API_KEY to os.environ so libraries that read
    directly from environment (like the OpenAI client used by PydanticAI)
    can find it.
    """
    import os

    settings = Settings()

    if (
        settings.openai_api_key
        and settings.openai_api_key != "sk-placeholder"  # pragma: allowlist secret
    ):
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key  # pragma: allowlist secret

    return settings
