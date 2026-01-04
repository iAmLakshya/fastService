from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert


class DatabaseDialect(str, Enum):
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    MYSQL = "mysql"


class UpsertStrategy(ABC):
    supports_returning: bool = True

    @abstractmethod
    def build_upsert(
        self,
        model: type,
        data: dict[str, Any],
        conflict_fields: list[str],
        update_fields: list[str],
    ) -> Any: ...


class PostgresUpsertStrategy(UpsertStrategy):
    supports_returning: bool = True

    def build_upsert(
        self,
        model: type,
        data: dict[str, Any],
        conflict_fields: list[str],
        update_fields: list[str],
    ) -> Any:
        stmt = pg_insert(model).values(**data)
        return stmt.on_conflict_do_update(
            index_elements=conflict_fields,
            set_={field: getattr(stmt.excluded, field) for field in update_fields},
        ).returning(model)


class SqliteUpsertStrategy(UpsertStrategy):
    supports_returning: bool = True

    def build_upsert(
        self,
        model: type,
        data: dict[str, Any],
        conflict_fields: list[str],
        update_fields: list[str],
    ) -> Any:
        stmt = sqlite_insert(model).values(**data)
        return stmt.on_conflict_do_update(
            index_elements=conflict_fields,
            set_={field: getattr(stmt.excluded, field) for field in update_fields},
        ).returning(model)


class MySQLUpsertStrategy(UpsertStrategy):
    supports_returning: bool = False

    def build_upsert(
        self,
        model: type,
        data: dict[str, Any],
        _conflict_fields: list[str],
        update_fields: list[str],
    ) -> Any:
        stmt = mysql_insert(model).values(**data)
        return stmt.on_duplicate_key_update(
            {field: getattr(stmt.inserted, field) for field in update_fields}
        )


def get_upsert_strategy(database_url: str) -> UpsertStrategy:
    if DatabaseDialect.POSTGRESQL in database_url:
        return PostgresUpsertStrategy()
    if DatabaseDialect.MYSQL in database_url:
        return MySQLUpsertStrategy()
    return SqliteUpsertStrategy()
