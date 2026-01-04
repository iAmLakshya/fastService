from app.infrastructure.persistence.repository.dialect import (
    DatabaseDialect,
    PostgresUpsertStrategy,
    SqliteUpsertStrategy,
    UpsertStrategy,
    get_upsert_strategy,
)
from app.infrastructure.persistence.repository.document import BaseDocumentRepository
from app.infrastructure.persistence.repository.kv import BaseKeyValueRepository
from app.infrastructure.persistence.repository.sql import BaseSQLRepository
from app.infrastructure.persistence.repository.type_protocols import (
    DocumentRepository,
    KeyValueRepository,
    SQLRepository,
)

__all__ = [
    "BaseDocumentRepository",
    "BaseKeyValueRepository",
    "BaseSQLRepository",
    "DatabaseDialect",
    "DocumentRepository",
    "KeyValueRepository",
    "PostgresUpsertStrategy",
    "SQLRepository",
    "SqliteUpsertStrategy",
    "UpsertStrategy",
    "get_upsert_strategy",
]
