from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.database import DatabasesSettings


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SERVER_")

    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1


class RateLimitSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RATELIMIT_")

    enabled: bool = False
    default: str = "100/minute"


class CORSSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CORS_")

    enabled: bool = True
    origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    allow_credentials: bool = False
    allow_methods: list[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE"]
    )
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])

    @model_validator(mode="after")
    def validate_cors_security(self) -> Self:
        """Reject insecure CORS configuration: wildcard origins with credentials."""
        if self.allow_credentials and "*" in self.origins:
            raise ValueError(
                "CORS misconfiguration: cannot use allow_credentials=True with "
                "wildcard origin '*'. Specify explicit origins or disable credentials."
            )
        return self


class LoggingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LOG_")

    level: str = "INFO"
    json_format: bool = False


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    name: str = Field("FastAPI Service", alias="APP_NAME")
    version: str = Field("1.0.0", alias="APP_VERSION")
    description: str = Field("Production-ready FastAPI service", alias="APP_DESCRIPTION")
    env: Literal["development", "staging", "production"] = Field("development", alias="APP_ENV")
    debug: bool = Field(False, alias="DEBUG")
    secret_key: str = Field("change-me-in-production", alias="SECRET_KEY")

    databases: DatabasesSettings = Field(default_factory=DatabasesSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    ratelimit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    @property
    def is_development(self) -> bool:
        return self.env == "development"

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @model_validator(mode="after")
    def validate_production_settings(self) -> Self:
        """Enforce secure configuration in production."""
        if self.env == "production":
            if self.secret_key == "change-me-in-production":
                raise ValueError(
                    "SECRET_KEY must be changed from default value in production"
                )
            if self.debug:
                raise ValueError("DEBUG must be False in production")
        return self
