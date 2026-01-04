from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.infrastructure.messaging.cache import close_redis
from app.infrastructure.messaging.tasks import close_task_pool
from app.infrastructure.observability.logging import get_logger
from app.infrastructure.persistence.adapters import (
    MongoAdapter,
    MongoConfig,
    RedisAdapter,
    RedisConfig,
    SQLAlchemyAdapter,
    SQLConfig,
    get_registry,
)
from app.infrastructure.persistence.model import Base

logger = get_logger(__name__)


async def _register_databases() -> None:
    registry = get_registry()

    if settings.databases.sql.enabled:
        sql_config = SQLConfig(
            url=settings.databases.sql.url,
            echo=settings.databases.sql.echo,
            pool_size=settings.databases.sql.pool_size,
            max_overflow=settings.databases.sql.max_overflow,
            pool_pre_ping=settings.databases.sql.pool_pre_ping,
            pool_recycle=settings.databases.sql.pool_recycle,
        )
        sql_adapter = SQLAlchemyAdapter(sql_config)
        registry.register(settings.databases.sql.name, sql_adapter, set_as_default=True)

    if settings.databases.mongo.enabled:
        mongo_config = MongoConfig(
            url=settings.databases.mongo.url,
            database=settings.databases.mongo.database,
            max_pool_size=settings.databases.mongo.max_pool_size,
            min_pool_size=settings.databases.mongo.min_pool_size,
        )
        mongo_adapter = MongoAdapter(mongo_config)
        registry.register(settings.databases.mongo.name, mongo_adapter)

    if settings.databases.redis.enabled:
        redis_config = RedisConfig(
            url=settings.databases.redis.url,
            decode_responses=settings.databases.redis.decode_responses,
            max_connections=settings.databases.redis.max_connections,
        )
        redis_adapter = RedisAdapter(redis_config)
        registry.register(settings.databases.redis.name, redis_adapter)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    await _register_databases()
    registry = get_registry()
    await registry.connect_all()

    for name, adapter in registry:
        if isinstance(adapter, SQLAlchemyAdapter):
            async with adapter.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("database_tables_created", adapter=name)

    logger.info("application_started", databases=registry.names)
    yield

    await registry.disconnect_all()
    await close_redis()
    await close_task_pool()
    logger.info("application_shutdown")
