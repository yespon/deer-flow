"""Tests for QuotaMiddleware."""

from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import ToolMessage

from deerflow.enterprise.quota_config import QuotaConfig, TenantQuota
from deerflow.enterprise.quota_middleware import QuotaMiddleware


class TestQuotaMiddleware:
    @pytest.fixture
    def quota_config(self):
        return QuotaConfig(
            enabled=True,
            default_quotas=TenantQuota(max_concurrent_sandboxes=5),
        )

    @pytest.fixture
    def middleware(self, quota_config):
        with patch("deerflow.enterprise.quota_middleware.get_quota_manager") as mock_get:
            mock_manager = Mock()
            mock_get.return_value = mock_manager
            middleware = QuotaMiddleware(quota_config)
            middleware._quota_manager = mock_manager
            return middleware

    def test_allows_sandbox_when_quota_available(self, middleware):
        middleware._quota_manager.acquire.return_value = True

        request = Mock()
        request.tool_call = {"name": "bash", "args": {"command": "ls"}, "id": "call_1"}
        handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="bash"))

        result = middleware.wrap_tool_call(request, handler)

        assert result.content == "ok"
        handler.assert_called_once()

    def test_blocks_sandbox_when_quota_exhausted(self, middleware):
        middleware._quota_manager.acquire.return_value = False
        middleware._quota_manager.get_usage.return_value = 6

        request = Mock()
        request.tool_call = {"name": "bash", "args": {"command": "ls"}, "id": "call_1"}
        handler = Mock()

        result = middleware.wrap_tool_call(request, handler)

        assert isinstance(result, ToolMessage)
        assert result.status == "error"
        assert "quota" in result.content.lower()
        handler.assert_not_called()

    def test_skips_when_quota_disabled(self):
        config = QuotaConfig(enabled=False)
        middleware = QuotaMiddleware(config)

        request = Mock()
        request.tool_call = {"name": "bash", "args": {}, "id": "call_1"}
        handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="bash"))

        result = middleware.wrap_tool_call(request, handler)

        assert result.content == "ok"

    def test_skips_non_sandbox_tools(self, middleware):
        request = Mock()
        request.tool_call = {"name": "ask_clarification", "args": {"question": "?"}, "id": "call_1"}
        handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="ask_clarification"))

        result = middleware.wrap_tool_call(request, handler)

        assert result.content == "ok"
        middleware._quota_manager.acquire.assert_not_called()

    def test_extracts_tenant_from_context(self, middleware):
        middleware._quota_manager.acquire.return_value = True

        with patch("deerflow.enterprise.quota_middleware.get_current_tenant") as mock_get_tenant:
            mock_tenant = Mock()
            mock_tenant.id = "tenant_abc"
            mock_get_tenant.return_value = mock_tenant

            request = Mock()
            request.tool_call = {"name": "bash", "args": {}, "id": "call_1"}
            handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="bash"))

            middleware.wrap_tool_call(request, handler)

            middleware._quota_manager.acquire.assert_called_with("tenant_abc", "concurrent_sandboxes", limit=5)

    def test_async_version_works(self, middleware):
        middleware._quota_manager.acquire.return_value = True

        request = Mock()
        request.tool_call = {"name": "bash", "args": {}, "id": "call_1"}

        async def async_handler(request):
            return ToolMessage(content="ok", tool_call_id="call_1", name="bash")

        import asyncio

        result = asyncio.run(middleware.awrap_tool_call(request, async_handler))

        assert result.content == "ok"
