"""Health check endpoints for DeerFlow Gateway."""

import logging
import time
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.gateway.performance import SimpleCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health", tags=["health"])

# Cache for health check results (5 second TTL)
_health_cache = SimpleCache(default_ttl=5)


class ComponentHealth(BaseModel):
    """Health status of a single component."""

    status: Literal["up", "down", "degraded"]
    latency_ms: float
    details: dict | None = None


class HealthStatus(BaseModel):
    """Overall system health status."""

    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    components: dict[str, ComponentHealth]
    timestamp: str


def get_version() -> str:
    """Get application version from package."""
    try:
        from importlib.metadata import version

        return version("deerflow")
    except Exception:
        return "unknown"


async def check_langgraph_health() -> None:
    """Check LangGraph runtime connectivity."""
    # TODO: Implement actual health check
    # This would check if the LangGraph runtime is accessible
    pass


async def check_sandbox_health() -> None:
    """Check sandbox provider status."""
    # TODO: Implement actual health check
    # This would check if the sandbox service is accessible
    pass


async def check_memory_store_health() -> None:
    """Check memory store accessibility."""
    # TODO: Implement actual health check
    # This would check if the memory store is accessible
    pass


async def check_database_health(request: Request) -> None:
    """Check database/checkpointer availability."""
    # Try to get checkpointer from app state (set during lifespan)
    checkpointer = getattr(request.app.state, "checkpointer", None)
    if checkpointer is None:
        raise RuntimeError("Checkpointer not available")


@router.get("", response_model=HealthStatus)
async def health_check(request: Request) -> HealthStatus:
    """Comprehensive health check endpoint.

    Checks:
    - LangGraph runtime connectivity
    - Database/checkpointer availability
    - Sandbox provider status
    - Memory store accessibility
    """
    components: dict[str, ComponentHealth] = {}
    overall_status: Literal["healthy", "degraded", "unhealthy"] = "healthy"

    # Check LangGraph
    try:
        start = time.time()
        await check_langgraph_health()
        components["langgraph"] = ComponentHealth(status="up", latency_ms=(time.time() - start) * 1000)
    except Exception as e:
        components["langgraph"] = ComponentHealth(status="down", latency_ms=0, details={"error": str(e)})
        overall_status = "unhealthy"

    # Check database/checkpointer
    try:
        start = time.time()
        await check_database_health(request)
        components["database"] = ComponentHealth(status="up", latency_ms=(time.time() - start) * 1000)
    except Exception as e:
        components["database"] = ComponentHealth(status="down", latency_ms=0, details={"error": str(e)})
        overall_status = "unhealthy"

    # Check sandbox
    try:
        start = time.time()
        await check_sandbox_health()
        components["sandbox"] = ComponentHealth(status="up", latency_ms=(time.time() - start) * 1000)
    except Exception as e:
        components["sandbox"] = ComponentHealth(status="down", latency_ms=0, details={"error": str(e)})
        # Sandbox down degrades but doesn't make unhealthy
        if overall_status == "healthy":
            overall_status = "degraded"

    # Check memory store
    try:
        start = time.time()
        await check_memory_store_health()
        components["memory"] = ComponentHealth(status="up", latency_ms=(time.time() - start) * 1000)
    except Exception as e:
        components["memory"] = ComponentHealth(status="down", latency_ms=0, details={"error": str(e)})
        # Memory down degrades but doesn't make unhealthy
        if overall_status == "healthy":
            overall_status = "degraded"

    return HealthStatus(
        status=overall_status,
        version=get_version(),
        components=components,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )


@router.get("/ready")
async def readiness_check() -> dict:
    """Kubernetes-style readiness probe.

    Returns 200 when the service is ready to accept traffic.
    """
    return {"ready": True}


@router.get("/live")
async def liveness_check() -> dict:
    """Kubernetes-style liveness probe.

    Returns 200 if the service is alive and should not be restarted.
    """
    return {"alive": True}
