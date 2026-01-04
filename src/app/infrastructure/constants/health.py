from enum import StrEnum


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    READY = "ready"
    LIVE = "live"
    CONNECTED = "connected"
