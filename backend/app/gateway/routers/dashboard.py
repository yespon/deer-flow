"""
Dashboard API endpoints for system monitoring and metrics.

Provides real-time system health, metrics, and status information
for the Prism dashboard.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.gateway.performance import ConnectionPool, SimpleCache

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# Cache for dashboard metrics (30 second TTL)
_metrics_cache = SimpleCache(default_ttl=30)


class SystemMetrics(BaseModel):
    """System performance metrics."""

    cpu_percent: float
    memory_percent: float
    disk_percent: float
    uptime_seconds: float


class ConnectionMetrics(BaseModel):
    """Connection pool metrics."""

    active_pools: int
    total_connections: int
    pool_names: list[str]


class CacheMetrics(BaseModel):
    """Cache performance metrics."""

    cache_size: int
    hit_rate: float | None


class DashboardResponse(BaseModel):
    """Dashboard data response."""

    timestamp: str
    health: dict[str, Any]
    system: SystemMetrics | None
    connections: ConnectionMetrics
    cache: CacheMetrics
    recent_errors: list[dict[str, Any]]


@router.get("/metrics", response_model=DashboardResponse)
async def get_dashboard_metrics(request: Request) -> DashboardResponse:
    """Get comprehensive dashboard metrics.

    Returns system health, performance metrics, and status information
    for the Prism dashboard.
    """
    # Get health status (reuse existing health check)
    from app.gateway.routers.health import health_check

    health_data = await health_check(request)

    # Get connection pool metrics
    conn_metrics = ConnectionMetrics(
        active_pools=len(ConnectionPool._pools),
        total_connections=sum(1 for _ in ConnectionPool._pools.values()),  # Simplified count
        pool_names=list(ConnectionPool._pools.keys()),
    )

    # Get cache metrics (simplified)
    cache_metrics = CacheMetrics(
        cache_size=len(_metrics_cache._cache),
        hit_rate=None,  # Would need tracking in real implementation
    )

    return DashboardResponse(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        health=health_data.model_dump(),
        system=None,  # Would need psutil in real implementation
        connections=conn_metrics,
        cache=cache_metrics,
        recent_errors=[],  # Would need error tracking in real implementation
    )


@router.get("/health-history")
async def get_health_history(
    minutes: int = 60,
) -> dict[str, list[dict[str, Any]]]:
    """Get historical health check data.

    Args:
        minutes: Number of minutes of history to return

    Returns:
        List of historical health check results with timestamps
    """
    # This is a placeholder - in a real implementation,
    # this would query a time-series database or log store
    return {
        "history": [],
        "period_minutes": minutes,
    }


@router.post("/cache/clear")
async def clear_dashboard_cache() -> dict[str, str]:
    """Clear the dashboard metrics cache."""
    _metrics_cache.clear()
    return {"status": "cache_cleared"}
