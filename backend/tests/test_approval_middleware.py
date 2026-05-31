"""Tests for ApprovalMiddleware - Human-in-Loop approval workflow."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import ToolMessage

from deerflow.agents.middlewares.approval_middleware import ApprovalMiddleware
from deerflow.enterprise.approval import ApprovalStatus

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _make_request(
    tool_name: str = "bash",
    args: dict | None = None,
    thread_id: str = "thread-1",
    tenant_id: str = "tenant-1",
) -> MagicMock:
    """Build a minimal ToolCallRequest mock."""
    request = MagicMock()
    request.tool_call = {
        "name": tool_name,
        "id": "call-123",
        "args": args or {"command": "echo hello"},
    }
    request.runtime = SimpleNamespace(
        context={"thread_id": thread_id, "tenant_id": tenant_id},
        config={"configurable": {"thread_id": thread_id, "tenant_id": tenant_id}},
        state={},
    )
    return request


def _make_handler(return_value: ToolMessage | None = None):
    """Create a sync handler mock."""
    if return_value is None:
        return_value = ToolMessage(
            content="ok",
            tool_call_id="call-123",
            name="bash",
        )
    handler = MagicMock(return_value=return_value)
    return handler


# -----------------------------------------------------------------------------
# ApprovalMiddleware tests
# -----------------------------------------------------------------------------


class TestApprovalMiddlewareInitialization:
    def test_initialization_enabled(self):
        mw = ApprovalMiddleware(enabled=True)
        assert mw.enabled is True
        assert mw._approval_engine is not None
        assert mw._state_manager is not None

    def test_initialization_disabled(self):
        mw = ApprovalMiddleware(enabled=False)
        assert mw.enabled is False


class TestApprovalMiddlewareDisabled:
    def test_disabled_middleware_passes_through(self):
        mw = ApprovalMiddleware(enabled=False)
        request = _make_request()
        handler = _make_handler()

        result = mw.wrap_tool_call(request, handler)

        handler.assert_called_once_with(request)
        assert result == handler.return_value


class TestApprovalMiddlewareNoRulesMatch:
    def test_no_approval_required_for_safe_tool(self):
        """Tools that don't match any approval rules should execute normally."""
        mw = ApprovalMiddleware(enabled=True)
        request = _make_request(
            tool_name="ls",
            args={"path": "/tmp"},
        )
        handler = _make_handler()

        # Clear default rules to ensure no matches
        with patch.object(
            mw._approval_engine,
            "check_rules",
            return_value=[],
        ):
            result = mw.wrap_tool_call(request, handler)

        handler.assert_called_once_with(request)
        assert result == handler.return_value


class TestApprovalMiddlewareApprovalRequired:
    def test_financial_transaction_requires_approval(self):
        """High-value financial transactions should require approval."""
        mw = ApprovalMiddleware(enabled=True)
        request = _make_request(
            tool_name="transfer_funds",
            args={"amount": 50000, "to": "account-123"},
        )
        handler = _make_handler()

        with patch.object(
            mw._state_manager,
            "suspend_execution",
            return_value=MagicMock(),
        ) as mock_suspend:
            result = mw.wrap_tool_call(request, handler)

        # Handler should NOT be called
        handler.assert_not_called()

        # Should return pending message
        assert isinstance(result, ToolMessage)
        assert result.status == "error"  # Error status to indicate operation didn't complete
        assert "Approval Required" in result.content
        assert "financial_transaction" in result.content

        # Should suspend execution
        mock_suspend.assert_called_once()

    def test_sensitive_data_access_requires_approval(self):
        """Database queries should require approval."""
        mw = ApprovalMiddleware(enabled=True)
        request = _make_request(
            tool_name="query_database",
            args={"query": "SELECT * FROM users"},
        )
        handler = _make_handler()

        with patch.object(
            mw._state_manager,
            "suspend_execution",
            return_value=MagicMock(),
        ) as mock_suspend:
            result = mw.wrap_tool_call(request, handler)

        # Handler should NOT be called
        handler.assert_not_called()

        # Should return pending message
        assert isinstance(result, ToolMessage)
        assert result.status == "error"
        assert "sensitive_data_access" in result.content

        # Should suspend execution
        mock_suspend.assert_called_once()


class TestApprovalMiddlewarePendingMessage:
    def test_pending_message_contains_request_id(self):
        """Pending message should include approval request ID."""
        mw = ApprovalMiddleware(enabled=True)
        request = _make_request(
            tool_name="transfer_funds",
            args={"amount": 50000},
        )
        handler = _make_handler()

        with patch.object(mw._state_manager, "suspend_execution"):
            result = mw.wrap_tool_call(request, handler)

        assert isinstance(result, ToolMessage)
        # Request ID should be in UUID format
        assert "Request ID:" in result.content
        # UUID pattern check
        import re

        uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        assert re.search(uuid_pattern, result.content)

    def test_pending_message_includes_tool_name(self):
        """Pending message should mention the tool being called."""
        mw = ApprovalMiddleware(enabled=True)
        request = _make_request(
            tool_name="export_data",  # This matches sensitive_data_access rule
            args={"table": "users"},
        )
        handler = _make_handler()

        with patch.object(mw._state_manager, "suspend_execution"):
            result = mw.wrap_tool_call(request, handler)

        assert isinstance(result, ToolMessage)
        assert "export_data" in result.content


class TestApprovalMiddlewareResumedExecution:
    def test_approved_execution_proceeds(self):
        """If approval is granted, tool should execute."""
        mw = ApprovalMiddleware(enabled=True)
        request = _make_request(
            tool_name="transfer_funds",
            args={"amount": 50000},
        )
        handler = _make_handler()

        # Create a mock approval with APPROVED status
        mock_approval = MagicMock()
        mock_approval.request_id = "req-123"
        mock_approval.status = ApprovalStatus.APPROVED
        mock_approval.approver = "finance_manager"

        with (
            patch.object(
                mw._state_manager,
                "list_pending",
                return_value=[
                    MagicMock(
                        thread_id="thread-1",
                        approval=mock_approval,
                    )
                ],
            ),
            patch.object(
                mw._approval_engine,
                "get_request",
                return_value=mock_approval,
            ),
        ):
            result = mw.wrap_tool_call(request, handler)

        # Handler should be called for approved requests
        handler.assert_called_once_with(request)
        assert isinstance(result, ToolMessage)
        assert "Approved" in result.content


class TestApprovalMiddlewareAsync:
    @pytest.mark.anyio
    async def test_async_disabled_passes_through(self):
        mw = ApprovalMiddleware(enabled=False)
        request = _make_request()
        handler = _make_handler()

        async def async_handler(req):
            return handler(req)

        result = await mw.awrap_tool_call(request, async_handler)

        handler.assert_called_once_with(request)
        assert result == handler.return_value

    @pytest.mark.anyio
    async def test_async_financial_transaction_requires_approval(self):
        """Async path should also require approval for financial transactions."""
        mw = ApprovalMiddleware(enabled=True)
        request = _make_request(
            tool_name="transfer_funds",
            args={"amount": 50000},
        )
        handler = _make_handler()

        async def async_handler(req):
            return handler(req)

        with patch.object(mw._state_manager, "suspend_execution"):
            result = await mw.awrap_tool_call(request, async_handler)

        handler.assert_not_called()
        assert isinstance(result, ToolMessage)
        assert result.status == "error"

    @pytest.mark.anyio
    async def test_async_approved_execution_proceeds(self):
        """Async path should execute approved requests."""
        mw = ApprovalMiddleware(enabled=True)
        request = _make_request(
            tool_name="transfer_funds",
            args={"amount": 50000},
        )
        handler = _make_handler()

        async def async_handler(req):
            return handler(req)

        # Create a mock approval with APPROVED status
        mock_approval = MagicMock()
        mock_approval.request_id = "req-123"
        mock_approval.status = ApprovalStatus.APPROVED

        with (
            patch.object(
                mw._state_manager,
                "list_pending",
                return_value=[
                    MagicMock(
                        thread_id="thread-1",
                        approval=mock_approval,
                    )
                ],
            ),
            patch.object(
                mw._approval_engine,
                "get_request",
                return_value=mock_approval,
            ),
        ):
            result = await mw.awrap_tool_call(request, async_handler)

        handler.assert_called_once()
        assert isinstance(result, ToolMessage)
        assert "Approved" in result.content


class TestApprovalMiddlewareEdgeCases:
    def test_missing_thread_id(self):
        """Should handle missing thread_id gracefully."""
        mw = ApprovalMiddleware(enabled=True)
        request = _make_request()
        request.runtime = SimpleNamespace(
            context={},
            config={},
            state={},
        )
        handler = _make_handler()

        with patch.object(mw._state_manager, "suspend_execution"):
            result = mw.wrap_tool_call(request, handler)

        # Should still work with "unknown" thread_id
        if isinstance(result, ToolMessage) and result.status == "error":
            assert "Approval Required" in result.content

    def test_missing_tool_call_id(self):
        """Should handle missing tool_call_id gracefully."""
        mw = ApprovalMiddleware(enabled=True)
        request = _make_request(
            tool_name="query_database",  # Use a tool that matches approval rules
            args={"query": "SELECT * FROM users"},
        )
        request.tool_call["id"] = None
        handler = _make_handler()

        with patch.object(mw._state_manager, "suspend_execution"):
            result = mw.wrap_tool_call(request, handler)

        assert isinstance(result, ToolMessage)
        # Should use "missing_id" fallback
        assert result.tool_call_id == "missing_id"

    def test_small_amount_no_approval(self):
        """Small financial amounts should not require approval."""
        mw = ApprovalMiddleware(enabled=True)
        request = _make_request(
            tool_name="transfer_funds",
            args={"amount": 500},  # Below 10000 threshold
        )
        handler = _make_handler()

        result = mw.wrap_tool_call(request, handler)

        # Should execute normally
        handler.assert_called_once_with(request)
        assert result == handler.return_value


class TestApprovalMiddlewareRuleMatching:
    def test_exact_threshold_does_not_require_approval(self):
        """Amount exactly at threshold should NOT require approval (rule is > 10000)."""
        mw = ApprovalMiddleware(enabled=True)
        request = _make_request(
            tool_name="transfer_funds",
            args={"amount": 10000},  # Exactly at threshold - rule is > not >=
        )
        handler = _make_handler()

        result = mw.wrap_tool_call(request, handler)

        # Should NOT require approval (rule is > 10000, not >=)
        handler.assert_called_once_with(request)
        assert result == handler.return_value

    def test_export_data_requires_approval(self):
        """Export data tool should require approval."""
        mw = ApprovalMiddleware(enabled=True)
        request = _make_request(
            tool_name="export_data",
            args={"table": "users"},
        )
        handler = _make_handler()

        with patch.object(mw._state_manager, "suspend_execution"):
            result = mw.wrap_tool_call(request, handler)

        assert isinstance(result, ToolMessage)
        assert result.status == "error"


class TestApprovalMiddlewareRejected:
    def test_rejected_request_handling(self):
        """Test handling of rejected approval requests."""
        mw = ApprovalMiddleware(enabled=True)

        # Create a mock rejected approval
        mock_approval = MagicMock()
        mock_approval.request_id = "req-123"
        mock_approval.status = ApprovalStatus.REJECTED
        mock_approval.approver = "security_manager"

        # Build rejection message
        message = mw._build_rejected_message(
            _make_request(),
            mock_approval,
        )

        assert isinstance(message, ToolMessage)
        assert message.status == "error"
        assert "Rejected" in message.content
        assert "security_manager" in message.content
