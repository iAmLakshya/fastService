from typing import Any

from fastapi import APIRouter

from app.infrastructure.constants import HealthStatus
from app.infrastructure.observability.logging import get_logger
from app.infrastructure.persistence.adapters import get_registry

logger = get_logger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict[str, Any]:
    registry = get_registry()
    health_results = await registry.health_check_all()

    all_healthy = all(health_results.values()) if health_results else True

    return {
        "status": HealthStatus.HEALTHY if all_healthy else HealthStatus.UNHEALTHY,
        "databases": {
            name: HealthStatus.CONNECTED if healthy else HealthStatus.UNHEALTHY
            for name, healthy in health_results.items()
        },
    }


@router.get("/health/ready")
async def readiness_check() -> dict[str, str]:
    return {"status": HealthStatus.READY}


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    return {"status": HealthStatus.LIVE}
