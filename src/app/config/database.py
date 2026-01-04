from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SQLSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DB_SQL_")

    enabled: bool = True
    name: str = "primary"
    url: str = "sqlite+aiosqlite:///./app.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    pool_pre_ping: bool = True
    pool_recycle: int = 3600


class MongoSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DB_MONGO_")

    enabled: bool = False
    name: str = "mongo"
    url: str = "mongodb://localhost:27017"
    database: str = "app"
    max_pool_size: int = 100
    min_pool_size: int = 0


class RedisDBSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DB_REDIS_")

    enabled: bool = False
    name: str = "redis"
    url: str = "redis://localhost:6379/0"
    decode_responses: bool = True
    max_connections: int = 10


class DatabasesSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    sql: SQLSettings = Field(default_factory=SQLSettings)
    mongo: MongoSettings = Field(default_factory=MongoSettings)
    redis: RedisDBSettings = Field(default_factory=RedisDBSettings)

    @property
    def enabled_databases(self) -> list[str]:
        enabled = []
        if self.sql.enabled:
            enabled.append(self.sql.name)
        if self.mongo.enabled:
            enabled.append(self.mongo.name)
        if self.redis.enabled:
            enabled.append(self.redis.name)
        return enabled
