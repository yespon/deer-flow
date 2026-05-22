"""Tenant context management for multi-tenancy.

This module provides tenant-scoped context similar to user_context.py,
enabling data isolation across multiple enterprise tenants.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Final, Generator, Literal


@dataclass(frozen=True, slots=True)
class Tenant:
    """Represents a single tenant (enterprise customer).

    Attributes:
        id: Unique tenant identifier (e.g., "tenant_123abc")
        name: Human-readable tenant name
        plan: Subscription tier ("free", "pro", "enterprise")
        isolation_mode: Data isolation strategy ("strict" or "relaxed")
    """

    id: str
    name: str
    plan: Literal["free", "pro", "enterprise"] = "pro"
    isolation_mode: Literal["strict", "relaxed"] = "relaxed"

    @property
    def namespace_prefix(self) -> str:
        """Return the prefix used for namespacing tenant resources."""
        return self.id

    def __str__(self) -> str:
        return f"Tenant({self.id}, {self.name})"


# ContextVar for storing current tenant in async tasks
_current_tenant: Final[ContextVar[Tenant | None]] = ContextVar(
    "deerflow_current_tenant",
    default=None,
)


def set_current_tenant(tenant: Tenant) -> Token[Tenant | None]:
    """Set the current tenant for this async task.

    Returns a reset token that should be passed to reset_current_tenant
    in a finally block to restore the previous context.

    Example:
        token = set_current_tenant(tenant)
        try:
            # ... do work with tenant context
        finally:
            reset_current_tenant(token)
    """
    return _current_tenant.set(tenant)


def reset_current_tenant(token: Token[Tenant | None]) -> None:
    """Restore the context to the state captured by token."""
    _current_tenant.reset(token)


def get_current_tenant() -> Tenant | None:
    """Return the current tenant, or None if unset.

    Safe to call in any context. Used by code paths that can proceed
    without a tenant (e.g., system operations, public endpoints).
    """
    return _current_tenant.get()


def require_current_tenant() -> Tenant:
    """Return the current tenant, or raise RuntimeError.

    Used by repository code that must not be called outside a
    tenant-authenticated context.
    """
    tenant = _current_tenant.get()
    if tenant is None:
        raise RuntimeError("operation requires tenant context but none is set")
    return tenant


@contextmanager
def tenant_context(
    tenant: Tenant | str,
    name: str = "",
    plan: Literal["free", "pro", "enterprise"] = "pro",
    isolation_mode: Literal["strict", "relaxed"] = "relaxed",
) -> Generator[Tenant, None, None]:
    """Context manager for temporarily setting the current tenant.

    Args:
        tenant: Either a Tenant object or a tenant ID string
        name: Tenant name (used only if tenant is a string)
        plan: Subscription tier (used only if tenant is a string)
        isolation_mode: Isolation strategy (used only if tenant is a string)

    Example:
        with tenant_context("tenant_123", name="Acme Corp"):
            # All operations within this block have tenant context
            do_work()
    """
    if isinstance(tenant, str):
        tenant = Tenant(
            id=tenant,
            name=name or tenant,
            plan=plan,
            isolation_mode=isolation_mode,
        )

    token = set_current_tenant(tenant)
    try:
        yield tenant
    finally:
        reset_current_tenant(token)


# Sentinel for auto-resolution (similar to user_context.py)
class _AutoSentinel:
    """Marker meaning 'resolve tenant_id from contextvar'."""

    _instance: _AutoSentinel | None = None

    def __new__(cls) -> _AutoSentinel:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "<AUTO>"


AUTO: Final[_AutoSentinel] = _AutoSentinel()


def resolve_tenant_id(
    value: str | None | _AutoSentinel,
    *,
    method_name: str = "operation",
) -> str | None:
    """Resolve tenant_id parameter using AUTO sentinel pattern.

    Three-state semantics:
    - AUTO (default): read from contextvar; raise if no tenant context
    - Explicit str: use provided value
    - None: no tenant filter (for system operations)
    """
    if isinstance(value, _AutoSentinel):
        tenant = _current_tenant.get()
        if tenant is None:
            raise RuntimeError(
                f"{method_name} called with tenant_id=AUTO but no tenant context is set; "
                "pass an explicit tenant_id or use tenant_context()"
            )
        return tenant.id
    return value
