from collections.abc import Iterator
from typing import Any, TypeVar

from app.infrastructure.persistence.adapters.protocols import (
    DatabaseAdapter,
    DatabaseType,
)

AdapterT = TypeVar("AdapterT")

DEFAULT_ADAPTER_NAME = "primary"


class AdapterNotFoundError(KeyError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Adapter '{name}' not found")


class AdapterAlreadyRegisteredError(ValueError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Adapter '{name}' already registered")


class DatabaseRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, DatabaseAdapter[Any]] = {}
        self._defaults: dict[DatabaseType, str] = {}

    def register(
        self,
        name: str,
        adapter: DatabaseAdapter[Any],
        *,
        set_as_default: bool = False,
        replace: bool = False,
    ) -> None:
        if name in self._adapters and not replace:
            raise AdapterAlreadyRegisteredError(name)
        self._adapters[name] = adapter
        if set_as_default or adapter.database_type not in self._defaults:
            self._defaults[adapter.database_type] = name

    def unregister(self, name: str) -> DatabaseAdapter[Any] | None:
        adapter = self._adapters.pop(name, None)
        if adapter and self._defaults.get(adapter.database_type) == name:
            del self._defaults[adapter.database_type]
        return adapter

    def get(self, name: str) -> DatabaseAdapter[Any]:
        if name not in self._adapters:
            raise AdapterNotFoundError(name)
        return self._adapters[name]

    def get_typed(self, name: str, adapter_type: type[AdapterT]) -> AdapterT:
        adapter = self.get(name)
        if not isinstance(adapter, adapter_type):
            raise TypeError(f"Adapter '{name}' is not of type {adapter_type.__name__}")
        return adapter

    def get_default(self, db_type: DatabaseType) -> DatabaseAdapter[Any]:
        if db_type not in self._defaults:
            raise AdapterNotFoundError(f"default:{db_type}")
        return self._adapters[self._defaults[db_type]]

    def get_sql(self, name: str | None = None) -> DatabaseAdapter[Any]:
        return self.get(name) if name else self.get_default(DatabaseType.SQL)

    def get_document(self, name: str | None = None) -> DatabaseAdapter[Any]:
        return self.get(name) if name else self.get_default(DatabaseType.DOCUMENT)

    def get_kv(self, name: str | None = None) -> DatabaseAdapter[Any]:
        return self.get(name) if name else self.get_default(DatabaseType.KEY_VALUE)

    def has(self, name: str) -> bool:
        return name in self._adapters

    def has_type(self, db_type: DatabaseType) -> bool:
        return db_type in self._defaults

    @property
    def names(self) -> list[str]:
        return list(self._adapters.keys())

    async def connect_all(self) -> None:
        for adapter in self._adapters.values():
            await adapter.connect()

    async def disconnect_all(self) -> None:
        for adapter in self._adapters.values():
            await adapter.disconnect()

    async def health_check_all(self) -> dict[str, bool]:
        return {name: await adapter.health_check() for name, adapter in self._adapters.items()}

    def clear(self) -> None:
        self._adapters.clear()
        self._defaults.clear()

    def __len__(self) -> int:
        return len(self._adapters)

    def __contains__(self, name: str) -> bool:
        return name in self._adapters

    def __iter__(self) -> Iterator[tuple[str, DatabaseAdapter[Any]]]:
        return iter(self._adapters.items())


_registry: DatabaseRegistry | None = None


def get_registry() -> DatabaseRegistry:
    global _registry
    if _registry is None:
        _registry = DatabaseRegistry()
    return _registry


def reset_registry() -> None:
    global _registry
    _registry = None
