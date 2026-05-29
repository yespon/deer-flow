"""Tests for ApprovalMiddleware."""

from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import ToolMessage

from deerflow.enterprise.approval import ApprovalStatus
from deerflow.enterprise.approval_middleware import ApprovalMiddleware


class TestApprovalMiddleware:
    @pytest.fixture
    def middleware(self):
        return ApprovalMiddleware(enabled=True)

    def test_allows_tool_call_when_no_rules_match(self, middleware):
        """Tool call should proceed when no approval rules match."""
        with patch("deerflow.enterprise.approval_middleware.get_approval_engine") as mock_engine:
            mock_engine.return_value.check_rules.return_value = []

            request = Mock()
            request.tool_call = {"name": "read_file", "args": {"path": "/tmp/test"}, "id": "call_1"}
            handler = Mock(return_value=ToolMessage(content="content", tool_call_id="call_1", name="read_file"))

            result = middleware.wrap_tool_call(request, handler)

            assert result.content == "content"
            handler.assert_called_once()

    def test_creates_approval_request_when_rule_matches(self, middleware):
        """Should create approval request and return pending message when rule matches."""
        with patch("deerflow.enterprise.approval_middleware.get_approval_engine") as mock_engine:
            mock_rule = Mock()
            mock_rule.name = "sensitive_data_access"
            mock_engine.return_value.check_rules.return_value = [mock_rule]

            mock_request = Mock()
            mock_request.request_id = "approval_123"
            mock_request.status = ApprovalStatus.PENDING
            mock_engine.return_value.create_request.return_value = mock_request

            with patch("deerflow.enterprise.approval_middleware.get_state_manager"):
                request = Mock()
                request.tool_call = {"name": "query_database", "args": {"sql": "SELECT *"}, "id": "call_1"}
                handler = Mock()

                result = middleware.wrap_tool_call(request, handler)

                assert isinstance(result, ToolMessage)
                assert "approval" in result.content.lower()
                assert "wait" in result.content.lower() or "pending" in result.content.lower()
                handler.assert_not_called()

    def test_skips_check_when_disabled(self):
        """Should skip approval check when middleware is disabled."""
        middleware = ApprovalMiddleware(enabled=False)

        request = Mock()
        request.tool_call = {"name": "query_database", "args": {}, "id": "call_1"}
        handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="query_database"))

        result = middleware.wrap_tool_call(request, handler)

        assert result.content == "ok"

    def test_extracts_tenant_and_thread_from_context(self, middleware):
        """Should extract tenant and thread ID from context."""
        with patch("deerflow.enterprise.approval_middleware.get_approval_engine") as mock_engine:
            mock_engine.return_value.check_rules.return_value = []

            with patch("deerflow.enterprise.approval_middleware.get_current_tenant") as mock_tenant:
                mock_tenant.return_value = Mock(id="tenant_abc")

                request = Mock()
                request.tool_call = {"name": "read_file", "args": {}, "id": "call_1"}
                handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="read_file"))

                middleware.wrap_tool_call(request, handler)

                # Verify context extraction happened
                mock_tenant.assert_called_once()

    def test_builds_pending_message_with_approval_id(self, middleware):
        """Pending message should include approval request ID."""
        mock_request = Mock()
        mock_request.request_id = "req_abc123"
        mock_request.rule_name = "sensitive_data_access"

        tool_call = {"name": "export_data", "args": {}, "id": "call_1"}
        result = middleware._build_pending_message(mock_request, tool_call)

        assert isinstance(result, ToolMessage)
        assert "req_abc123" in result.content
        assert "sensitive_data_access" in result.content
        assert result.status == "error"

    def test_async_version_creates_approval_request(self, middleware):
        """Async version should also create approval requests."""
        with patch("deerflow.enterprise.approval_middleware.get_approval_engine") as mock_engine:
            mock_rule = Mock()
            mock_rule.name = "financial_transaction"
            mock_engine.return_value.check_rules.return_value = [mock_rule]

            mock_request = Mock()
            mock_request.request_id = "approval_456"
            mock_request.status = ApprovalStatus.PENDING
            mock_engine.return_value.create_request.return_value = mock_request

            with patch("deerflow.enterprise.approval_middleware.get_state_manager"):
                request = Mock()
                request.tool_call = {"name": "transfer_funds", "args": {"amount": 50000}, "id": "call_1"}

                async def async_handler(request):
                    return ToolMessage(content="ok", tool_call_id="call_1", name="transfer_funds")

                import asyncio

                result = asyncio.run(middleware.awrap_tool_call(request, async_handler))

                assert isinstance(result, ToolMessage)
                assert "approval" in result.content.lower()

    def test_suspends_execution_when_approval_created(self, middleware):
        """Should suspend execution and save state when approval is created."""
        with patch("deerflow.enterprise.approval_middleware.get_approval_engine") as mock_engine:
            mock_rule = Mock()
            mock_rule.name = "test_rule"
            mock_engine.return_value.check_rules.return_value = [mock_rule]

            mock_request = Mock()
            mock_request.request_id = "approval_789"
            mock_request.status = ApprovalStatus.PENDING
            mock_engine.return_value.create_request.return_value = mock_request

            with patch("deerflow.enterprise.approval_middleware.get_state_manager") as mock_state:
                mock_state_manager = Mock()
                mock_state.return_value = mock_state_manager

                request = Mock()
                request.tool_call = {"name": "bash", "args": {"command": "rm -rf /"}, "id": "call_1"}
                handler = Mock()

                middleware.wrap_tool_call(request, handler)

                # Verify state was suspended
                mock_state_manager.suspend_execution.assert_called_once()

    def test_maps_tool_name_correctly(self, middleware):
        """Should correctly extract tool name from request."""
        with patch("deerflow.enterprise.approval_middleware.get_approval_engine") as mock_engine:
            mock_engine.return_value.check_rules.return_value = []

            request = Mock()
            request.tool_call = {"name": "custom_tool", "args": {}, "id": "call_1"}
            handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="custom_tool"))

            middleware.wrap_tool_call(request, handler)

            # Verify check_rules was called with correct tool call
            args = mock_engine.return_value.check_rules.call_args
            assert args[0][0].get("name") == "custom_tool"
