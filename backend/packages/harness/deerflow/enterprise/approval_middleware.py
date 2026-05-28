"""Approval middleware for Human-in-Loop workflow.

Intercepts tool calls that match approval rules and suspends execution
pending human approval.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from deerflow.agents.thread_state import ThreadState
from deerflow.enterprise.approval import ApprovalRequest, ApprovalStatus, get_approval_engine
from deerflow.enterprise.approval_state import get_state_manager
from deerflow.enterprise.tenancy import get_current_tenant


logger = logging.getLogger(__name__)


class ApprovalPendingError(Exception):
    """Raised when a tool call requires approval.

    This exception signals that execution should be suspended pending approval.
    """

    def __init__(self, approval_id: str, message: str | None = None) -> None:
        self.approval_id = approval_id
        self.message = message or f"Tool call requires approval (ID: {approval_id})"
        super().__init__(self.message)


class ApprovalMiddleware(AgentMiddleware[ThreadState]):
    """Middleware that enforces approval rules on tool calls.

    Checks if tool calls match any approval rules and either:
    - Allows execution if no rules match
    - Suspends execution and creates approval request if rules match
    """

    state_schema = ThreadState

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._approval_engine: Any | None = None

    def _get_approval_engine(self) -> Any:
        """Get approval engine (lazy loading for testability)."""
        if self._approval_engine is None:
            self._approval_engine = get_approval_engine()
        return self._approval_engine

    def _get_tenant_id(self) -> str:
        """Extract tenant ID from current context."""
        tenant = get_current_tenant()
        return tenant.id if tenant else "default"

    def _get_thread_id(self) -> str | None:
        """Extract thread ID from current context."""
        # Try to get from thread state context
        # This will be set by the runtime
        return None  # Will be populated from state when available

    def _build_pending_message(
        self,
        approval_request: ApprovalRequest,
        tool_call: dict,
    ) -> ToolMessage:
        """Build error message for pending approval."""
        tool_call_id = str(tool_call.get("id") or "missing_id")
        tool_name = tool_call.get("name", "unknown")

        content = (
            f"⏳ Approval Required\n\n"
            f"Tool '{tool_name}' requires approval before execution.\n"
            f"Rule: {approval_request.rule_name}\n"
            f"Approval ID: {approval_request.request_id}\n\n"
            f"Please wait for an administrator to approve this request."
        )

        return ToolMessage(
            content=content,
            tool_call_id=tool_call_id,
            name=tool_name,
            status="error",
        )

    def _suspend_execution(
        self,
        thread_id: str | None,
        approval_request: ApprovalRequest,
        tool_call: dict,
    ) -> None:
        """Suspend execution and save state for later resumption."""
        state_manager = get_state_manager()

        # Create checkpoint with minimal state
        # Full checkpoint would come from thread state
        checkpoint = {
            "tool_call": tool_call,
            "approval_request_id": approval_request.request_id,
        }

        state_manager.suspend_execution(
            thread_id=thread_id or "unknown",
            checkpoint=checkpoint,
            approval=approval_request,
        )

        logger.info(
            "Execution suspended for approval: request_id=%s, tenant_id=%s, thread_id=%s",
            approval_request.request_id,
            approval_request.tenant_id,
            thread_id,
        )

    def _check_and_create_approval(
        self,
        tool_call: dict,
        tenant_id: str,
        thread_id: str | None,
    ) -> ApprovalRequest | None:
        """Check if approval is needed and create request if so.

        Returns:
            ApprovalRequest if approval is required, None otherwise.
        """
        # Check if any rules match
        approval_engine = self._get_approval_engine()
        matching_rules = approval_engine.check_rules(tool_call)

        if not matching_rules:
            return None

        # Use the first matching rule
        rule = matching_rules[0]

        # Create approval request
        approval_request = approval_engine.create_request(
            rule_name=rule.name,
            tenant_id=tenant_id,
            thread_id=thread_id or "unknown",
            tool_call=tool_call,
        )

        logger.info(
            "Approval request created: request_id=%s, rule=%s, tool=%s",
            approval_request.request_id,
            rule.name,
            tool_call.get("name", "unknown"),
        )

        return approval_request

    @override
    def wrap_tool_call(
        self,
        request,
        handler: Callable,
    ):
        """Wrap tool call with approval check."""
        if not self.enabled:
            return handler(request)

        tool_call = request.tool_call
        tool_name = tool_call.get("name", "")

        tenant_id = self._get_tenant_id()
        thread_id = self._get_thread_id()

        # Check if approval is needed
        approval_request = self._check_and_create_approval(
            tool_call, tenant_id, thread_id
        )

        if approval_request:
            # Approval required - suspend execution
            self._suspend_execution(thread_id, approval_request, tool_call)

            logger.warning(
                "Tool call blocked pending approval: tool=%s, approval_id=%s",
                tool_name,
                approval_request.request_id,
            )

            return self._build_pending_message(approval_request, tool_call)

        # No approval needed - proceed
        logger.debug(
            "Tool call allowed: tool=%s, tenant=%s",
            tool_name, tenant_id
        )
        return handler(request)

    @override
    async def awrap_tool_call(
        self,
        request,
        handler: Callable,
    ):
        """Async version of wrap_tool_call."""
        if not self.enabled:
            return await handler(request)

        tool_call = request.tool_call
        tool_name = tool_call.get("name", "")

        tenant_id = self._get_tenant_id()
        thread_id = self._get_thread_id()

        # Check if approval is needed
        approval_request = self._check_and_create_approval(
            tool_call, tenant_id, thread_id
        )

        if approval_request:
            # Approval required - suspend execution
            self._suspend_execution(thread_id, approval_request, tool_call)

            logger.warning(
                "Tool call blocked pending approval (async): tool=%s, approval_id=%s",
                tool_name,
                approval_request.request_id,
            )

            return self._build_pending_message(approval_request, tool_call)

        # No approval needed - proceed
        logger.debug(
            "Tool call allowed (async): tool=%s, tenant=%s",
            tool_name, tenant_id
        )
        return await handler(request)
