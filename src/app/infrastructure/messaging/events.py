import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

EventHandler = Callable[[Any], Coroutine[Any, Any, None]]

_handlers: dict[str, list[EventHandler]] = defaultdict(list)


def on(event: str) -> Callable[[EventHandler], EventHandler]:
    def decorator(fn: EventHandler) -> EventHandler:
        _handlers[event].append(fn)
        return fn

    return decorator


async def emit(event: str, payload: Any) -> None:
    handlers = _handlers.get(event, [])
    if handlers:
        await asyncio.gather(*[handler(payload) for handler in handlers])


def clear_handlers() -> None:
    _handlers.clear()


def get_handlers(event: str) -> list[EventHandler]:
    return _handlers.get(event, [])
