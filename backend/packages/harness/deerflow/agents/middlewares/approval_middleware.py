"""ApprovalMiddleware - Human-in-Loop approval workflow.

Intercepts tool calls matching approval rules and suspends execution
pending human approval.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

from deerflow.agents.thread_state import ThreadState
from deerflow.enterprise.approval import (
    ApprovalRequest,
    ApprovalStatus,
    get_approval_engine,
)
from deerflow.enterprise.approval_state import get_state_manager

logger = logging.getLogger(__name__)


class ApprovalMiddleware(AgentMiddleware[ThreadState]):
    """Human-in-Loop approval middleware.

    For each tool call:
    1. Check against registered approval rules
    2. If rules match, create approval request and suspend execution
    3. Return pending message to agent with approval details

    The suspended execution can be resumed via the approval API
    after human review.
    """

    state_schema = ThreadState

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._approval_engine = get_approval_engine()
        self._state_manager = get_state_manager()

    def _get_thread_id(self, request: ToolCallRequest) -> str | None:
        """Extract thread_id from request runtime."""
        runtime = request.runtime
        if runtime is None:
            return None
        ctx = getattr(runtime, "context", None) or {}
        thread_id = ctx.get("thread_id") if isinstance(ctx, dict) else None
        if thread_id is None:
            cfg = getattr(runtime, "config", None) or {}
            thread_id = cfg.get("configurable", {}).get("thread_id")
        return thread_id

    def _get_tenant_id(self, request: ToolCallRequest) -> str | None:
        """Extract tenant_id from request runtime."""
        runtime = request.runtime
        if runtime is None:
            return None
        ctx = getattr(runtime, "context", None) or {}
        tenant_id = ctx.get("tenant_id") if isinstance(ctx, dict) else None
        if tenant_id is None:
            cfg = getattr(runtime, "config", None) or {}
            tenant_id = cfg.get("configurable", {}).get("tenant_id")
        return tenant_id

    def _build_pending_message(
        self,
        request: ToolCallRequest,
        approval: ApprovalRequest,
    ) -> ToolMessage:
        """Build a pending message for approval."""
        tool_call_id = str(request.tool_call.get("id") or "missing_id")
        tool_name = request.tool_call.get("name", "unknown")

        content = (
            f"⏳ **Approval Required**\n\n"
            f"Tool call `{tool_name}` requires human approval.\n\n"
            f"**Request ID:** `{approval.request_id}`\n"
            f"**Rule:** `{approval.rule_name}`\n"
            f"**Status:** `{approval.status.value}`\n\n"
            f"Please review and approve/reject via the approval API."
        )

        return ToolMessage(
            content=content,
            tool_call_id=tool_call_id,
            name=tool_name,
            status="error",  # Use error status to indicate operation didn't complete
        )

    def _build_approved_message(
        self,
        request: ToolCallRequest,
        result: ToolMessage | Command,
    ) -> ToolMessage | Command:
        """Build an approved message wrapping the actual result."""
        if not isinstance(result, ToolMessage):
            return result

        approved_note = "\n\n✅ **Approved** - Executed after human review."

        if isinstance(result.content, list):
            new_content = list(result.content) + [{"type": "text", "text": approved_note}]
        else:
            new_content = str(result.content) + approved_note

        return ToolMessage(
            content=new_content,
            tool_call_id=result.tool_call_id,
            name=result.name,
            status=result.status,
        )

    def _build_rejected_message(
        self,
        request: ToolCallRequest,
        approval: ApprovalRequest,
    ) -> ToolMessage:
        """Build a rejection message."""
        tool_call_id = str(request.tool_call.get("id") or "missing_id")
        tool_name = request.tool_call.get("name", "unknown")

        content = f"❌ **Approval Rejected**\n\nTool call `{tool_name}` was rejected by {approval.approver}.\n\n**Reason:** Human reviewer denied this operation."

        return ToolMessage(
            content=content,
            tool_call_id=tool_call_id,
            name=tool_name,
            status="error",
        )

    def _check_approval(
        self,
        request: ToolCallRequest,
    ) -> tuple[ApprovalRequest | None, bool]:
        """Check if tool call requires approval.

        Returns (approval_request, requires_approval).
        If requires_approval is True, approval_request is the pending request.
        """
        # Flatten tool call args for rule checking
        # Rules check fields like "amount" and "tool" at the top level
        tool_name = request.tool_call.get("name", "")
        tool_call = {
            "name": tool_name,
            "tool": tool_name,  # Alias for rules that check "tool" field
            **(request.tool_call.get("args") or {}),
        }

        # Check rules
        matching_rules = self._approval_engine.check_rules(tool_call)

        if not matching_rules:
            return None, False

        # Use the first matching rule
        rule = matching_rules[0]
        thread_id = self._get_thread_id(request) or "unknown"
        tenant_id = self._get_tenant_id(request) or "default"

        # Create approval request with full tool call info
        full_tool_call = {
            "name": request.tool_call.get("name", ""),
            "args": request.tool_call.get("args", {}),
        }
        approval = self._approval_engine.create_request(
            rule_name=rule.name,
            tenant_id=tenant_id,
            thread_id=thread_id,
            tool_call=full_tool_call,
        )

        # Suspend execution state
        # Note: checkpoint would be passed from the runtime in real implementation
        checkpoint: dict = {}
        self._state_manager.suspend_execution(
            thread_id=thread_id,
            checkpoint=checkpoint,
            approval=approval,
        )

        logger.info(
            "[ApprovalMiddleware] Suspended execution for approval: request_id=%s rule=%s thread=%s",
            approval.request_id,
            rule.name,
            thread_id,
        )

        return approval, True

    def _check_resumed_execution(
        self,
        request: ToolCallRequest,
    ) -> ApprovalRequest | None:
        """Check if there's a resumed execution for this tool call.

        Returns the approval request if found and approved, None otherwise.
        """
        tool_call_id = request.tool_call.get("id")
        if not tool_call_id:
            return None

        # Check for pending approvals with matching tool call ID
        # In real implementation, this would check a proper mapping
        pending = self._state_manager.list_pending()

        for state in pending:
            if state.thread_id == self._get_thread_id(request):
                approval = self._approval_engine.get_request(state.approval.request_id)
                if approval and approval.status == ApprovalStatus.APPROVED:
                    return approval

        return None

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        if not self.enabled:
            return handler(request)

        # Check if this is a resumed execution
        resumed_approval = self._check_resumed_execution(request)

        if resumed_approval:
            # Execute the tool call
            logger.info(
                "[ApprovalMiddleware] Executing approved request: %s",
                resumed_approval.request_id,
            )
            result = handler(request)
            return self._build_approved_message(request, result)

        # Check if approval is required
        approval, requires_approval = self._check_approval(request)

        if requires_approval and approval:
            # Return pending message without executing
            return self._build_pending_message(request, approval)

        # No approval required, proceed normally
        return handler(request)

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        if not self.enabled:
            return await handler(request)

        # Check if this is a resumed execution
        resumed_approval = self._check_resumed_execution(request)

        if resumed_approval:
            # Execute the tool call
            logger.info(
                "[ApprovalMiddleware] Executing approved request: %s",
                resumed_approval.request_id,
            )
            result = await handler(request)
            return self._build_approved_message(request, result)

        # Check if approval is required
        approval, requires_approval = self._check_approval(request)

        if requires_approval and approval:
            # Return pending message without executing
            return self._build_pending_message(request, approval)

        # No approval required, proceed normally
        return await handler(request)
