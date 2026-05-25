"""Middleware for identifying and setting tenant context.

This middleware runs early in the request chain to establish tenant context
for all downstream operations.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from deerflow.enterprise.tenancy import (
    Tenant,
    reset_current_tenant,
    set_current_tenant,
)
from deerflow.enterprise.tenant_config import TenancyConfig

if TYPE_CHECKING:
    pass


class TenantResolver:
    """Resolves tenant from incoming requests."""

    def __init__(self, config: TenancyConfig) -> None:
        self.config = config

    def resolve(self, request: Any) -> Tenant:
        """Extract tenant from request and return Tenant object.

        Resolution order:
        1. Custom header (X-Tenant-ID)
        2. Domain-based resolution
        3. Default tenant
        """
        # Try header resolution
        tenant_id = self._resolve_from_header(request)
        if tenant_id:
            tenant_config = self.config.get_tenant(tenant_id)
            if tenant_config is None:
                raise ValueError(f"Unknown tenant: {tenant_id}")
            return Tenant(
                id=tenant_config.id,
                name=tenant_config.name,
                plan=tenant_config.plan,
                isolation_mode=tenant_config.isolation_mode,
            )

        # Return default tenant
        default = self.config.default_tenant
        return Tenant(
            id=default.id,
            name=default.name,
            plan=default.plan,
            isolation_mode=default.isolation_mode,
        )

    def _resolve_from_header(self, request: Any) -> str | None:
        """Extract tenant ID from custom header."""
        headers = getattr(request, "headers", {}) or {}
        # Handle both dict and Headers objects
        if hasattr(headers, "get"):
            tenant_id = headers.get(self.config.header_name)
        else:
            tenant_id = headers.get(self.config.header_name)
        return tenant_id


class TenantIdentificationMiddleware:
    """Middleware that establishes tenant context for requests.

    This middleware should run after authentication but before any
    tenant-aware operations.
    """

    def __init__(self, config: TenancyConfig) -> None:
        self.config = config
        self.resolver = TenantResolver(config)

    def __call__(
        self,
        request: Any,
        next_middleware: Callable[[Any], Any],
    ) -> Any:
        """Process request with tenant context."""
        if not self.config.enabled:
            # Multi-tenancy disabled - skip resolution
            return next_middleware(request)

        # Resolve tenant
        tenant = self.resolver.resolve(request)

        # Set context and proceed
        token = set_current_tenant(tenant)
        try:
            # Attach tenant to request for convenience
            request.tenant = tenant
            return next_middleware(request)
        finally:
            reset_current_tenant(token)

    async def __acall__(
        self,
        request: Any,
        next_middleware: Callable[[Any], Any],
    ) -> Any:
        """Async version of middleware call."""
        if not self.config.enabled:
            return await next_middleware(request)

        tenant = self.resolver.resolve(request)
        token = set_current_tenant(tenant)
        try:
            request.tenant = tenant
            return await next_middleware(request)
        finally:
            reset_current_tenant(token)
