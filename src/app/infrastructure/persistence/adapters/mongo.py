from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.infrastructure.persistence.adapters.protocols import DatabaseType

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase


@dataclass(frozen=True)
class MongoConfig:
    url: str
    database: str
    max_pool_size: int = 100
    min_pool_size: int = 0


class MongoAdapter:
    def __init__(self, config: MongoConfig) -> None:
        self._config = config
        self._client: AsyncIOMotorClient | None = None
        self._database: AsyncIOMotorDatabase | None = None

    @property
    def database_type(self) -> DatabaseType:
        return DatabaseType.DOCUMENT

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    @property
    def config(self) -> MongoConfig:
        return self._config

    async def connect(self) -> None:
        if self._client is not None:
            return
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
        except ImportError as e:
            raise ImportError("motor is required for MongoDB support: pip install motor") from e
        self._client = AsyncIOMotorClient(
            self._config.url,
            maxPoolSize=self._config.max_pool_size,
            minPoolSize=self._config.min_pool_size,
        )
        self._database = self._client[self._config.database]

    async def disconnect(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._database = None

    async def dispose(self) -> None:
        await self.disconnect()

    async def health_check(self) -> bool:
        if not self.is_connected or self._client is None:
            return False
        try:
            await self._client.admin.command("ping")
            return True
        except Exception:
            return False

    def get_connection(self) -> "AsyncIOMotorDatabase":
        if self._database is None:
            raise RuntimeError("Adapter not connected")
        return self._database

    def collection(self, name: str) -> "AsyncIOMotorCollection":
        return self.get_connection()[name]
