import asyncio
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, connection_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[connection_id] = websocket
        logger.info("websocket_connected", connection_id=connection_id)

    async def disconnect(self, connection_id: str) -> None:
        async with self._lock:
            self._connections.pop(connection_id, None)
        logger.info("websocket_disconnected", connection_id=connection_id)

    async def send_personal(self, connection_id: str, message: dict[str, Any]) -> bool:
        async with self._lock:
            websocket = self._connections.get(connection_id)
        if websocket:
            try:
                await websocket.send_json(message)
                return True
            except WebSocketDisconnect:
                await self.disconnect(connection_id)
        return False

    async def broadcast(self, message: dict[str, Any], exclude: set[str] | None = None) -> int:
        exclude = exclude or set()
        sent = 0
        disconnected = []

        async with self._lock:
            connections = list(self._connections.items())

        for connection_id, websocket in connections:
            if connection_id in exclude:
                continue
            try:
                await websocket.send_json(message)
                sent += 1
            except WebSocketDisconnect:
                disconnected.append(connection_id)

        for connection_id in disconnected:
            await self.disconnect(connection_id)

        return sent

    @property
    def active_connections(self) -> int:
        return len(self._connections)

    def is_connected(self, connection_id: str) -> bool:
        return connection_id in self._connections


manager = ConnectionManager()
