import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "request_completed",
            method=scope["method"],
            path=scope["path"],
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
        )
