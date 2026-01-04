import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.infrastructure.observability.logging import clear_request_id, set_request_id

REQUEST_ID_HEADER = b"x-request-id"


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = None
        for header_name, header_value in scope.get("headers", []):
            if header_name == REQUEST_ID_HEADER:
                request_id = header_value.decode()
                break

        if not request_id:
            request_id = str(uuid.uuid4())

        set_request_id(request_id)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((REQUEST_ID_HEADER, request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            clear_request_id()
