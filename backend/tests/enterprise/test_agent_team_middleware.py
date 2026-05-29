"""Tests for AgentTeamMiddleware."""

from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import ToolMessage

from deerflow.enterprise.agent_team_middleware import AgentTeamMiddleware


class TestAgentTeamMiddleware:
    @pytest.fixture
    def middleware(self):
        return AgentTeamMiddleware(enabled=True)

    def test_skips_simple_tasks(self, middleware):
        """Should skip agent team for simple tasks."""
        request = Mock()
        request.tool_call = {"name": "read_file", "args": {"path": "/tmp/test"}, "id": "call_1"}
        handler = Mock(return_value=ToolMessage(content="content", tool_call_id="call_1", name="read_file"))

        result = middleware.wrap_tool_call(request, handler)

        assert result.content == "content"
        handler.assert_called_once()

    def test_detects_complex_tasks(self, middleware):
        """Should detect complex tasks based on keywords."""
        with patch.object(middleware, "_is_complex_task") as mock_is_complex:
            mock_is_complex.return_value = True

            with patch.object(middleware, "_execute_with_agent_team") as mock_execute:
                # _execute_with_agent_team should return string (content)
                mock_execute.return_value = "Team result"

                request = Mock()
                request.tool_call = {"name": "task", "args": {"description": "Complex multi-step task"}, "id": "call_1"}
                handler = Mock()

                result = middleware.wrap_tool_call(request, handler)

                assert isinstance(result, ToolMessage)
                assert result.content == "Team result"
                mock_execute.assert_called_once()

    def test_skips_when_disabled(self):
        """Should skip when middleware is disabled."""
        middleware = AgentTeamMiddleware(enabled=False)

        request = Mock()
        request.tool_call = {"name": "task", "args": {"description": "Complex task"}, "id": "call_1"}
        handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="task"))

        result = middleware.wrap_tool_call(request, handler)

        assert result.content == "ok"

    def test_complexity_detection_keywords(self, middleware):
        """Should detect complexity based on keywords."""
        complex_tasks = [
            "Research and analyze market trends",
            "Build a complete web application",
            "Implement a multi-step workflow",
            "Create a comprehensive report",
        ]

        for task in complex_tasks:
            assert middleware._is_complex_task(task), f"Should detect complexity in: {task}"

    def test_simple_task_detection(self, middleware):
        """Should identify simple tasks."""
        simple_tasks = [
            "Read a file",
            "List directory",
            "Simple query",
        ]

        for task in simple_tasks:
            assert not middleware._is_complex_task(task), f"Should not detect complexity in: {task}"

    @pytest.mark.asyncio
    async def test_async_version(self, middleware):
        """Should support async execution."""
        with patch.object(middleware, "_is_complex_task") as mock_is_complex:
            mock_is_complex.return_value = False

            request = Mock()
            request.tool_call = {"name": "read_file", "args": {}, "id": "call_1"}

            async def async_handler(request):
                return ToolMessage(content="ok", tool_call_id="call_1", name="read_file")

            result = await middleware.awrap_tool_call(request, async_handler)

            assert result.content == "ok"

    def test_extracts_task_description(self, middleware):
        """Should extract task description from tool call."""
        tool_call = {
            "name": "task",
            "args": {"description": "Analyze this data and create a report"},
            "id": "call_1",
        }

        description = middleware._extract_task_description(tool_call)

        assert description == "Analyze this data and create a report"

    def test_falls_back_to_handler_on_error(self, middleware):
        """Should fall back to original handler on orchestrator error."""
        with patch.object(middleware, "_is_complex_task") as mock_is_complex:
            mock_is_complex.return_value = True

            with patch.object(middleware, "_execute_with_agent_team") as mock_execute:
                mock_execute.side_effect = Exception("Orchestrator failed")

                request = Mock()
                request.tool_call = {"name": "task", "args": {"description": "Complex task"}, "id": "call_1"}
                handler = Mock(return_value=ToolMessage(content="fallback", tool_call_id="call_1", name="task"))

                result = middleware.wrap_tool_call(request, handler)

                # Should fall back to handler
                assert result.content == "fallback"

    def test_only_handles_task_tool(self, middleware):
        """Should only process 'task' tool calls."""
        request = Mock()
        request.tool_call = {"name": "bash", "args": {"command": "ls"}, "id": "call_1"}
        handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="bash"))

        result = middleware.wrap_tool_call(request, handler)

        # Should not check complexity for non-task tools
        assert result.content == "ok"
