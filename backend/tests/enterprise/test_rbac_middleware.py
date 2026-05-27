"""Tests for RBACMiddleware."""

from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import ToolMessage

from deerflow.enterprise.rbac_middleware import RBACMiddleware


class TestRBACMiddleware:
    @pytest.fixture
    def middleware(self):
        return RBACMiddleware(enabled=True)

    def test_allows_permitted_tool_call(self, middleware):
        with patch("deerflow.enterprise.rbac_middleware.check_permission") as mock_check:
            mock_check.return_value = True

            request = Mock()
            request.tool_call = {"name": "read_file", "args": {"path": "/tmp/test"}, "id": "call_1"}
            handler = Mock(return_value=ToolMessage(content="content", tool_call_id="call_1", name="read_file"))

            result = middleware.wrap_tool_call(request, handler)

            assert result.content == "content"
            handler.assert_called_once()
            mock_check.assert_called_once()

    def test_denies_unpermitted_tool_call(self, middleware):
        with patch("deerflow.enterprise.rbac_middleware.check_permission") as mock_check:
            mock_check.return_value = False

            request = Mock()
            request.tool_call = {"name": "bash", "args": {"command": "rm -rf /"}, "id": "call_1"}
            handler = Mock()

            result = middleware.wrap_tool_call(request, handler)

            assert isinstance(result, ToolMessage)
            assert result.status == "error"
            assert "permission" in result.content.lower()
            handler.assert_not_called()

    def test_skips_check_when_rbac_disabled(self):
        middleware = RBACMiddleware(enabled=False)

        request = Mock()
        request.tool_call = {"name": "bash", "args": {}, "id": "call_1"}
        handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="bash"))

        result = middleware.wrap_tool_call(request, handler)

        assert result.content == "ok"

    def test_maps_bash_to_sandbox_execute(self, middleware):
        with patch("deerflow.enterprise.rbac_middleware.check_permission") as mock_check:
            mock_check.return_value = True

            request = Mock()
            request.tool_call = {"name": "bash", "args": {}, "id": "call_1"}
            handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="bash"))

            middleware.wrap_tool_call(request, handler)

            args = mock_check.call_args
            assert args[0][2] == "sandbox"
            assert args[0][3] == "execute"

    def test_maps_read_file_to_sandbox_read(self, middleware):
        with patch("deerflow.enterprise.rbac_middleware.check_permission") as mock_check:
            mock_check.return_value = True

            request = Mock()
            request.tool_call = {"name": "read_file", "args": {}, "id": "call_1"}
            handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="read_file"))

            middleware.wrap_tool_call(request, handler)

            args = mock_check.call_args
            assert args[0][2] == "sandbox"
            assert args[0][3] == "read"

    def test_maps_task_to_agent_execute(self, middleware):
        with patch("deerflow.enterprise.rbac_middleware.check_permission") as mock_check:
            mock_check.return_value = True

            request = Mock()
            request.tool_call = {"name": "task", "args": {}, "id": "call_1"}
            handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="task"))

            middleware.wrap_tool_call(request, handler)

            args = mock_check.call_args
            assert args[0][2] == "agent"
            assert args[0][3] == "execute"

    def test_extracts_user_and_tenant_from_context(self, middleware):
        with patch("deerflow.enterprise.rbac_middleware.check_permission") as mock_check:
            mock_check.return_value = True
            with patch("deerflow.enterprise.rbac_middleware.get_effective_user_id") as mock_user:
                mock_user.return_value = "user_123"
                with patch("deerflow.enterprise.rbac_middleware.get_current_tenant") as mock_tenant:
                    mock_tenant.return_value = Mock(id="tenant_abc")

                    request = Mock()
                    request.tool_call = {"name": "read_file", "args": {}, "id": "call_1"}
                    handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="read_file"))

                    middleware.wrap_tool_call(request, handler)

                    args = mock_check.call_args
                    assert args[0][0] == "user_123"
                    assert args[0][1] == "tenant_abc"

    def test_async_version_works(self, middleware):
        with patch("deerflow.enterprise.rbac_middleware.check_permission") as mock_check:
            mock_check.return_value = True

            request = Mock()
            request.tool_call = {"name": "read_file", "args": {}, "id": "call_1"}

            async def async_handler(request):
                return ToolMessage(content="ok", tool_call_id="call_1", name="read_file")

            import asyncio
            result = asyncio.run(middleware.awrap_tool_call(request, async_handler))

            assert result.content == "ok"
