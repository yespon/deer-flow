"""Quota enforcement middleware for sandbox operations."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, override

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

from deerflow.agents.thread_state import ThreadState
from deerflow.enterprise.quota import QuotaManager, QuotaExceededError
from deerflow.enterprise.quota_config import QuotaConfig
from deerflow.enterprise.tenancy import get_current_tenant

if TYPE_CHECKING:
    from redis import Redis


logger = logging.getLogger(__name__)

# Tools that consume sandbox quota
_SANDBOX_TOOLS = {"bash", "str_replace", "write_file", "read_file", "ls"}


def get_quota_manager(redis_client: Redis | None = None) -> QuotaManager:
    """Get or create global QuotaManager instance."""
    if not hasattr(get_quota_manager, "_instance"):
        get_quota_manager._instance = QuotaManager(redis_client)
    return get_quota_manager._instance


class QuotaMiddleware(AgentMiddleware[ThreadState]):
    """Middleware that enforces tenant resource quotas.

    Tracks and limits concurrent sandbox usage per tenant.
    """

    state_schema = ThreadState

    def __init__(
        self,
        config: QuotaConfig,
        quota_manager: QuotaManager | None = None,
    ) -> None:
        self.config = config
        self._quota_manager = quota_manager or get_quota_manager()

    def _is_sandbox_tool(self, tool_name: str) -> bool:
        """Check if tool consumes sandbox quota."""
        return tool_name in _SANDBOX_TOOLS

    def _get_tenant_id(self) -> str:
        """Extract tenant ID from current context."""
        tenant = get_current_tenant()
        return tenant.id if tenant else "default"

    def _get_quota_limit(self) -> int:
        """Get quota limit for concurrent sandboxes."""
        return self.config.default_quotas.max_concurrent_sandboxes

    def _build_quota_exceeded_message(
        self,
        request: ToolCallRequest,
        error: QuotaExceededError,
    ) -> ToolMessage:
        """Build error message for quota exceeded."""
        tool_call_id = str(request.tool_call.get("id") or "missing_id")
        tool_name = request.tool_call.get("name", "unknown")

        content = (
            f"❌ Quota Exceeded\n\n"
            f"Cannot execute '{tool_name}': sandbox quota exceeded.\n"
            f"Current usage: {error.current}/{error.limit} concurrent sandboxes.\n\n"
            f"Please wait for existing operations to complete or contact your administrator."
        )

        return ToolMessage(
            content=content,
            tool_call_id=tool_call_id,
            name=tool_name,
            status="error",
        )

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        if not self.config.enabled:
            return handler(request)

        tool_name = request.tool_call.get("name", "")

        if not self._is_sandbox_tool(tool_name):
            return handler(request)

        tenant_id = self._get_tenant_id()
        limit = self._get_quota_limit()

        # Try to acquire quota
        acquired = self._quota_manager.acquire(
            tenant_id, "concurrent_sandboxes", limit=limit
        )

        if not acquired:
            # Build error from current usage
            current = self._quota_manager.get_usage(tenant_id, "concurrent_sandboxes")
            error = QuotaExceededError(
                tenant_id=tenant_id,
                resource="concurrent_sandboxes",
                limit=limit,
                current=current,
            )
            return self._build_quota_exceeded_message(request, error)

        try:
            return handler(request)
        finally:
            # Release quota after execution
            self._quota_manager.release(tenant_id, "concurrent_sandboxes")

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        if not self.config.enabled:
            return await handler(request)

        tool_name = request.tool_call.get("name", "")

        if not self._is_sandbox_tool(tool_name):
            return await handler(request)

        tenant_id = self._get_tenant_id()
        limit = self._get_quota_limit()

        acquired = self._quota_manager.acquire(
            tenant_id, "concurrent_sandboxes", limit=limit
        )

        if not acquired:
            current = self._quota_manager.get_usage(tenant_id, "concurrent_sandboxes")
            error = QuotaExceededError(
                tenant_id=tenant_id,
                resource="concurrent_sandboxes",
                limit=limit,
                current=current,
            )
            return self._build_quota_exceeded_message(request, error)

        try:
            return await handler(request)
        finally:
            self._quota_manager.release(tenant_id, "concurrent_sandboxes")
