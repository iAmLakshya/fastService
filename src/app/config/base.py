from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DB_")

    url: str = "sqlite+aiosqlite:///./app.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SERVER_")

    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False


class AppSettings(BaseSettings):
    """Main application settings composed from domain-specific settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    name: str = Field("FastAPI Service", alias="APP_NAME")
    env: Literal["development", "staging", "production"] = Field(
        "development", alias="APP_ENV"
    )
    debug: bool = Field(False, alias="DEBUG")
    secret_key: str = Field("change-me-in-production", alias="SECRET_KEY")

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)

    @property
    def is_development(self) -> bool:
        return self.env == "development"

    @property
    def is_production(self) -> bool:
        return self.env == "production"
