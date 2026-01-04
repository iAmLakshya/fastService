from abc import ABC, abstractmethod
from typing import Any

from app.infrastructure.constants import Seeder as SeederDefaults
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

_seeders: dict[str, type["Seeder"]] = {}


class Seeder(ABC):
    name: str
    order: int = SeederDefaults.DEFAULT_ORDER

    @abstractmethod
    async def run(self) -> int:
        pass

    async def clear(self) -> int:
        return 0


def register_seeder(seeder_class: type[Seeder]) -> type[Seeder]:
    _seeders[seeder_class.name] = seeder_class
    return seeder_class


def get_seeder(name: str) -> type[Seeder] | None:
    return _seeders.get(name)


def get_all_seeders() -> list[type[Seeder]]:
    return sorted(_seeders.values(), key=lambda s: s.order)


def get_seeder_names() -> list[str]:
    return list(_seeders.keys())


async def run_seeder(name: str, **kwargs: Any) -> int:
    seeder_class = get_seeder(name)
    if not seeder_class:
        raise ValueError(f"Seeder '{name}' not found. Available: {get_seeder_names()}")

    seeder = seeder_class()
    count = await seeder.run(**kwargs)
    logger.info("seeder_completed", seeder=name, count=count)
    return count


async def run_all_seeders(**kwargs: Any) -> dict[str, int]:
    results = {}
    for seeder_class in get_all_seeders():
        seeder = seeder_class()
        count = await seeder.run(**kwargs)
        results[seeder_class.name] = count
        logger.info("seeder_completed", seeder=seeder_class.name, count=count)
    return results


async def clear_seeder(name: str) -> int:
    seeder_class = get_seeder(name)
    if not seeder_class:
        raise ValueError(f"Seeder '{name}' not found")

    seeder = seeder_class()
    return await seeder.clear()


async def clear_all_seeders() -> dict[str, int]:
    results = {}
    for seeder_class in reversed(get_all_seeders()):
        seeder = seeder_class()
        count = await seeder.clear()
        results[seeder_class.name] = count
    return results
