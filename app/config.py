from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "nagp-user-service"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # API
    api_v1_prefix: str = "/api/v1"
    allowed_origins: list[str] = ["*"]

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/userservice"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30
    database_echo: bool = False

    # Security
    secret_key: str = "change-me-in-production-minimum-32-chars"
    access_token_expire_minutes: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
