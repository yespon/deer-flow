"""Tests for KnowledgeRetrievalMiddleware."""

from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import ToolMessage

from deerflow.enterprise.knowledge_retrieval_middleware import KnowledgeRetrievalMiddleware


class TestKnowledgeRetrievalMiddleware:
    @pytest.fixture
    def middleware(self):
        return KnowledgeRetrievalMiddleware(enabled=True)

    def test_skips_when_disabled(self):
        """Should skip retrieval when middleware is disabled."""
        middleware = KnowledgeRetrievalMiddleware(enabled=False)

        request = Mock()
        request.tool_call = {"name": "read_file", "args": {}, "id": "call_1"}
        handler = Mock(return_value=ToolMessage(content="ok", tool_call_id="call_1", name="read_file"))

        result = middleware.wrap_tool_call(request, handler)

        assert result.content == "ok"

    def test_skips_non_llm_tools(self, middleware):
        """Should skip retrieval for non-LLM tools."""
        request = Mock()
        request.tool_call = {"name": "bash", "args": {"command": "ls"}, "id": "call_1"}
        handler = Mock(return_value=ToolMessage(content="output", tool_call_id="call_1", name="bash"))

        result = middleware.wrap_tool_call(request, handler)

        assert result.content == "output"
        handler.assert_called_once()

    def test_extracts_query_from_messages(self, middleware):
        """Should extract query from conversation messages."""
        messages = [
            Mock(type="system", content="You are a helpful assistant"),
            Mock(type="human", content="What is machine learning?"),
        ]

        query = middleware._extract_query(messages)

        assert "machine learning" in query.lower()

    def test_extracts_last_user_message(self, middleware):
        """Should use the last user message as query."""
        messages = [
            Mock(type="human", content="First question"),
            Mock(type="ai", content="First answer"),
            Mock(type="human", content="Second question"),
        ]

        query = middleware._extract_query(messages)

        assert query == "Second question"

    def test_formats_knowledge_context(self, middleware):
        """Should format knowledge chunks into context."""
        from deerflow.enterprise.knowledge_base import DocumentChunk

        chunks = [
            DocumentChunk(chunk_id="c1", doc_id="d1", content="Knowledge content 1"),
            DocumentChunk(chunk_id="c2", doc_id="d1", content="Knowledge content 2"),
        ]

        context = middleware._format_knowledge_context(chunks)

        assert "<enterprise_knowledge>" in context
        assert "Knowledge content 1" in context
        assert "Knowledge content 2" in context
        assert "</enterprise_knowledge>" in context

    def test_empty_knowledge_returns_none(self, middleware):
        """Should return None when no knowledge found."""
        context = middleware._format_knowledge_context([])

        assert context is None

    @pytest.mark.asyncio
    async def test_retrieves_knowledge_for_llm_calls(self, middleware):
        """Should retrieve knowledge for LLM tool calls."""
        with patch.object(middleware, "_get_knowledge_base") as mock_kb:
            mock_kb.return_value.search.return_value = [Mock(content="Knowledge about AI")]

            # Mock state with messages
            mock_state = Mock()
            mock_state.messages = [Mock(type="human", content="Tell me about AI")]

            with patch.object(middleware, "_get_current_state", return_value=mock_state):
                request = Mock()
                request.tool_call = {"name": "chat", "args": {}, "id": "call_1"}

                # Create a handler that captures the modified request
                captured_kwargs = {}

                def handler(req, **kwargs):
                    captured_kwargs.update(kwargs)
                    return ToolMessage(content="AI is...", tool_call_id="call_1", name="chat")

                result = await middleware.awrap_tool_call(request, handler)

                assert result.content == "AI is..."

    def test_query_rewrite_simple(self, middleware):
        """Should rewrite query to be search-friendly."""
        query = "What is the best way to learn Python programming?"

        rewritten = middleware._rewrite_query(query)

        assert "Python programming" in rewritten

    def test_query_rewrite_removes_punctuation(self, middleware):
        """Should clean punctuation from query."""
        query = "Hello?! How are you???"

        rewritten = middleware._rewrite_query(query)

        assert "???" not in rewritten
        assert "?!" not in rewritten

    def test_only_processes_llm_tools(self, middleware):
        """Should only process tools that call LLMs."""
        assert middleware._is_llm_tool("chat") is True
        assert middleware._is_llm_tool("ask") is True
        assert middleware._is_llm_tool("bash") is False
        assert middleware._is_llm_tool("read_file") is False

    def test_gets_tenant_from_context(self, middleware):
        """Should extract tenant ID from context."""
        with patch("deerflow.enterprise.knowledge_retrieval_middleware.get_current_tenant") as mock_tenant:
            mock_tenant.return_value = Mock(id="tenant_abc")

            tenant_id = middleware._get_tenant_id()

            assert tenant_id == "tenant_abc"

    def test_default_tenant_when_none(self, middleware):
        """Should use default tenant when not set."""
        with patch("deerflow.enterprise.knowledge_retrieval_middleware.get_current_tenant", return_value=None):
            tenant_id = middleware._get_tenant_id()

            assert tenant_id == "default"
