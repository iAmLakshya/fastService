from abc import abstractmethod
from collections.abc import AsyncIterator
from enum import StrEnum
from typing import Protocol, TypeVar, runtime_checkable

ConnectionT = TypeVar("ConnectionT")


class DatabaseType(StrEnum):
    SQL = "sql"
    DOCUMENT = "document"
    KEY_VALUE = "kv"


@runtime_checkable
class DatabaseAdapter(Protocol[ConnectionT]):  # type: ignore[misc]
    @property
    @abstractmethod
    def database_type(self) -> DatabaseType: ...

    @property
    @abstractmethod
    def is_connected(self) -> bool: ...

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def health_check(self) -> bool: ...


@runtime_checkable
class TransactionalAdapter(Protocol[ConnectionT]):  # type: ignore[misc]
    @abstractmethod
    def session(self) -> AsyncIterator[ConnectionT]: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...


@runtime_checkable
class DisposableAdapter(Protocol):
    @abstractmethod
    async def dispose(self) -> None: ...


class FullDatabaseAdapter(  # type: ignore[misc]
    DatabaseAdapter[ConnectionT],
    TransactionalAdapter[ConnectionT],
    DisposableAdapter,
    Protocol[ConnectionT],
):
    pass
