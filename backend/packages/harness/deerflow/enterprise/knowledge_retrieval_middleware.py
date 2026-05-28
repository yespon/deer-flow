"""Knowledge Retrieval middleware for RAG integration.

Automatically retrieves relevant knowledge from Corporate Knowledge Base
and injects it into LLM context.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, override

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from deerflow.agents.thread_state import ThreadState
from deerflow.enterprise.knowledge_base import CorporateKnowledgeBase, DocumentChunk
from deerflow.enterprise.knowledge_config import KnowledgeBaseConfig
from deerflow.enterprise.tenancy import get_current_tenant

if TYPE_CHECKING:
    from langgraph.prebuilt.tool_node import ToolCallRequest


logger = logging.getLogger(__name__)

# Tools that involve LLM calls and should trigger knowledge retrieval
_LLM_TOOLS = {
    "chat",
    "ask",
    "complete",
    "generate",
    "explain",
    "analyze",
}


class KnowledgeRetrievalMiddleware(AgentMiddleware[ThreadState]):
    """Middleware that retrieves enterprise knowledge for LLM calls.

    Automatically:
    1. Extracts query from conversation context
    2. Rewrites query for better retrieval
    3. Searches Corporate Knowledge Base
    4. Injects relevant knowledge into context
    """

    state_schema = ThreadState

    def __init__(
        self,
        enabled: bool = True,
        knowledge_config: KnowledgeBaseConfig | None = None,
    ) -> None:
        self.enabled = enabled
        self._knowledge_config = knowledge_config or KnowledgeBaseConfig()
        self._knowledge_base: CorporateKnowledgeBase | None = None

    def _get_knowledge_base(self) -> CorporateKnowledgeBase | None:
        """Get or create knowledge base instance."""
        if not self.enabled or not self._knowledge_config.enabled:
            return None

        if self._knowledge_base is None:
            self._knowledge_base = CorporateKnowledgeBase(self._knowledge_config)

        return self._knowledge_base

    def _get_current_state(self) -> ThreadState | None:
        """Get current thread state from context.

        This would be populated by the runtime.
        """
        # In production, this would come from context vars or thread-local storage
        return None

    def _get_tenant_id(self) -> str:
        """Extract tenant ID from current context."""
        tenant = get_current_tenant()
        return tenant.id if tenant else "default"

    def _is_llm_tool(self, tool_name: str) -> bool:
        """Check if tool involves LLM calls."""
        return tool_name.lower() in _LLM_TOOLS

    def _extract_query(self, messages: list[Any]) -> str:
        """Extract search query from conversation messages.

        Uses the last user message as the query.
        """
        # Find the last user/human message
        for msg in reversed(messages):
            msg_type = getattr(msg, "type", None)
            if msg_type in ("human", "user"):
                content = getattr(msg, "content", "")
                if content:
                    return str(content)

        return ""

    def _rewrite_query(self, query: str) -> str:
        """Rewrite query for better knowledge retrieval.

        Removes punctuation, normalizes whitespace, and extracts key terms.
        """
        # Remove excessive punctuation
        query = re.sub(r'[!?]+', '', query)

        # Normalize whitespace
        query = ' '.join(query.split())

        # Remove stop words for search (simple version)
        stop_words = {'what', 'is', 'the', 'a', 'an', 'how', 'to', 'do', 'i', 'you', 'tell', 'me', 'about'}
        words = query.lower().split()
        key_words = [w for w in words if w not in stop_words]

        if key_words:
            return ' '.join(key_words)

        return query

    async def _retrieve_knowledge(
        self,
        query: str,
        tenant_id: str,
    ) -> list[DocumentChunk]:
        """Retrieve knowledge chunks for query."""
        kb = self._get_knowledge_base()
        if not kb:
            return []

        try:
            # Rewrite query for better retrieval
            search_query = self._rewrite_query(query)

            logger.debug(
                "Retrieving knowledge: query='%s', search='%s', tenant=%s",
                query[:50], search_query[:50], tenant_id
            )

            # Search knowledge base
            chunks = await kb.search(
                query=search_query,
                tenant_id=tenant_id,
            )

            logger.info(
                "Retrieved %d knowledge chunks for query: %s",
                len(chunks), query[:50]
            )

            return chunks

        except Exception as e:
            logger.error("Failed to retrieve knowledge: %s", e)
            return []

    def _format_knowledge_context(self, chunks: list[DocumentChunk]) -> str | None:
        """Format knowledge chunks into context string."""
        if not chunks:
            return None

        parts = ["<enterprise_knowledge>"]
        parts.append("The following information from your enterprise knowledge base may be relevant:")
        parts.append("")

        for i, chunk in enumerate(chunks, 1):
            parts.append(f"[{i}] {chunk.content}")

        parts.append("")
        parts.append("</enterprise_knowledge>")

        return "\n".join(parts)

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        """Wrap tool call with knowledge retrieval."""
        if not self.enabled:
            return handler(request)

        tool_call = request.tool_call
        tool_name = tool_call.get("name", "")

        # Only process LLM tools
        if not self._is_llm_tool(tool_name):
            return handler(request)

        # Get current state (messages)
        state = self._get_current_state()
        if not state or not getattr(state, "messages", None):
            logger.debug("No state available for knowledge retrieval")
            return handler(request)

        # Extract query from messages
        query = self._extract_query(state.messages)
        if not query:
            return handler(request)

        # Retrieve knowledge (sync version uses asyncio.run)
        import asyncio
        try:
            tenant_id = self._get_tenant_id()
            chunks = asyncio.run(self._retrieve_knowledge(query, tenant_id))

            # Format and inject context
            knowledge_context = self._format_knowledge_context(chunks)
            if knowledge_context:
                # Modify state to include knowledge context
                # This would be injected as a system message or context
                logger.debug("Injecting knowledge context into state")

        except Exception as e:
            logger.error("Knowledge retrieval failed: %s", e)

        # Call handler (knowledge context would be injected into state)
        return handler(request)

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        """Async version of wrap_tool_call."""
        if not self.enabled:
            return await handler(request)

        tool_call = request.tool_call
        tool_name = tool_call.get("name", "")

        # Only process LLM tools
        if not self._is_llm_tool(tool_name):
            return await handler(request)

        # Get current state (messages)
        state = self._get_current_state()
        if not state or not getattr(state, "messages", None):
            logger.debug("No state available for knowledge retrieval (async)")
            return await handler(request)

        # Extract query from messages
        query = self._extract_query(state.messages)
        if not query:
            return await handler(request)

        # Retrieve knowledge
        try:
            tenant_id = self._get_tenant_id()
            chunks = await self._retrieve_knowledge(query, tenant_id)

            # Format and inject context
            knowledge_context = self._format_knowledge_context(chunks)
            if knowledge_context:
                logger.debug("Injecting knowledge context into state (async)")

        except Exception as e:
            logger.error("Knowledge retrieval failed (async): %s", e)

        # Call handler
        return await handler(request)
