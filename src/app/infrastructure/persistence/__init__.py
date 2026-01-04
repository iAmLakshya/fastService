from app.infrastructure.persistence.adapters import (
    DatabaseAdapter,
    DatabaseRegistry,
    DatabaseType,
    MongoAdapter,
    MongoConfig,
    RedisAdapter,
    RedisConfig,
    SQLAlchemyAdapter,
    SQLConfig,
    get_registry,
    reset_registry,
)
from app.infrastructure.persistence.document import BaseDocument, SoftDeletableDocument
from app.infrastructure.persistence.model import (
    Base,
    Model,
    SoftDeletableModel,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)
from app.infrastructure.persistence.repository.document import BaseDocumentRepository
from app.infrastructure.persistence.repository.kv import BaseKeyValueRepository
from app.infrastructure.persistence.repository.sql import BaseSQLRepository
from app.infrastructure.persistence.repository.type_protocols import (
    DocumentRepository,
    KeyValueRepository,
    SQLRepository,
)
from app.infrastructure.persistence.service import BaseService

__all__ = [
    "Base",
    "BaseDocument",
    "BaseDocumentRepository",
    "BaseKeyValueRepository",
    "BaseSQLRepository",
    "BaseService",
    "DatabaseAdapter",
    "DatabaseRegistry",
    "DatabaseType",
    "DocumentRepository",
    "KeyValueRepository",
    "Model",
    "MongoAdapter",
    "MongoConfig",
    "RedisAdapter",
    "RedisConfig",
    "SQLAlchemyAdapter",
    "SQLConfig",
    "SQLRepository",
    "SoftDeletableDocument",
    "SoftDeletableModel",
    "SoftDeleteMixin",
    "TimestampMixin",
    "UUIDMixin",
    "get_registry",
    "reset_registry",
]
