"""RBAC permission checking middleware for tool calls."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

from deerflow.agents.thread_state import ThreadState
from deerflow.enterprise.rbac import check_permission
from deerflow.enterprise.tenancy import get_current_tenant
from deerflow.runtime.user_context import get_effective_user_id

logger = logging.getLogger(__name__)


# Tool name to (resource, action) mapping
_TOOL_PERMISSION_MAP: dict[str, tuple[str, str]] = {
    "bash": ("sandbox", "execute"),
    "str_replace": ("sandbox", "execute"),
    "write_file": ("sandbox", "execute"),
    "read_file": ("sandbox", "read"),
    "ls": ("sandbox", "read"),
    "task": ("agent", "execute"),
    "setup_agent": ("agent", "create"),
    "update_agent": ("agent", "update"),
    "ask_clarification": ("interaction", "execute"),
    "present_files": ("file", "read"),
    "view_image": ("file", "read"),
}


def _map_tool_to_resource(tool_name: str) -> tuple[str, str]:
    """Map tool name to (resource, action) tuple."""
    return _TOOL_PERMISSION_MAP.get(tool_name, ("tool", "execute"))


class RBACMiddleware(AgentMiddleware[ThreadState]):
    """Middleware that enforces RBAC permissions on tool calls."""

    state_schema = ThreadState

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def _get_user_id(self) -> str:
        """Extract user ID from current context."""
        return get_effective_user_id() or "anonymous"

    def _get_tenant_id(self) -> str:
        """Extract tenant ID from current context."""
        tenant = get_current_tenant()
        return tenant.id if tenant else "default"

    def _build_permission_denied_message(
        self,
        request: ToolCallRequest,
        user_id: str,
        resource: str,
        action: str,
    ) -> ToolMessage:
        """Build error message for permission denied."""
        tool_call_id = str(request.tool_call.get("id") or "missing_id")
        tool_name = request.tool_call.get("name", "unknown")

        content = f"❌ Permission Denied\n\nYou don't have permission to execute '{tool_name}'.\nRequired: {resource}:{action}\nUser: {user_id}\n\nContact your administrator if you need access."

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
        if not self.enabled:
            return handler(request)

        tool_name = request.tool_call.get("name", "")
        resource, action = _map_tool_to_resource(tool_name)

        user_id = self._get_user_id()
        tenant_id = self._get_tenant_id()

        allowed = check_permission(user_id, tenant_id, resource, action)

        if not allowed:
            logger.warning("RBAC denied: user=%s tenant=%s resource=%s action=%s tool=%s", user_id, tenant_id, resource, action, tool_name)
            return self._build_permission_denied_message(request, user_id, resource, action)

        logger.debug("RBAC allowed: user=%s tenant=%s resource=%s action=%s tool=%s", user_id, tenant_id, resource, action, tool_name)
        return handler(request)

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        if not self.enabled:
            return await handler(request)

        tool_name = request.tool_call.get("name", "")
        resource, action = _map_tool_to_resource(tool_name)

        user_id = self._get_user_id()
        tenant_id = self._get_tenant_id()

        allowed = check_permission(user_id, tenant_id, resource, action)

        if not allowed:
            logger.warning("RBAC denied (async): user=%s tenant=%s resource=%s action=%s tool=%s", user_id, tenant_id, resource, action, tool_name)
            return self._build_permission_denied_message(request, user_id, resource, action)

        return await handler(request)
