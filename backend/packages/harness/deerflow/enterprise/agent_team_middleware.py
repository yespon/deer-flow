"""Agent Team middleware for parallel task execution.

Automatically detects complex tasks and routes them to Agent Teams
for parallel execution.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, override

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from deerflow.agents.thread_state import ThreadState
from deerflow.enterprise.agent_team_orchestrator import AgentTeamOrchestrator
from deerflow.enterprise.task_decomposer import TaskDecomposer
from deerflow.enterprise.tenancy import get_current_tenant

if TYPE_CHECKING:
    from langgraph.prebuilt.tool_node import ToolCallRequest


logger = logging.getLogger(__name__)

# Keywords that indicate a complex task suitable for Agent Teams
_COMPLEX_TASK_KEYWORDS = {
    "research",
    "analyze",
    "build",
    "implement",
    "create",
    "develop",
    "multi-step",
    "workflow",
    "comprehensive",
    "complete",
    "complex",
}

# Simple task keywords that should NOT use Agent Teams
_SIMPLE_TASK_KEYWORDS = {
    "read",
    "list",
    "simple",
    "quick",
    "check",
    "get",
    "show",
}


class AgentTeamMiddleware(AgentMiddleware[ThreadState]):
    """Middleware that routes complex tasks to Agent Teams for parallel execution.

    Detects complex tasks based on keywords and:
    1. Decomposes the task into sub-tasks
    2. Executes sub-tasks in parallel using Agent Teams
    3. Aggregates results and returns to caller
    """

    state_schema = ThreadState

    def __init__(
        self,
        enabled: bool = True,
        max_parallel: int = 3,
    ) -> None:
        self.enabled = enabled
        self.max_parallel = max_parallel
        self._decomposer: TaskDecomposer | None = None
        self._orchestrator: AgentTeamOrchestrator | None = None

    def _get_decomposer(self) -> TaskDecomposer:
        """Get or create TaskDecomposer."""
        if self._decomposer is None:
            self._decomposer = TaskDecomposer()
        return self._decomposer

    def _get_orchestrator(self) -> AgentTeamOrchestrator:
        """Get or create AgentTeamOrchestrator."""
        if self._orchestrator is None:
            self._orchestrator = AgentTeamOrchestrator(max_parallel=self.max_parallel)
        return self._orchestrator

    def _is_complex_task(self, description: str) -> bool:
        """Determine if a task is complex enough to use Agent Teams.

        Uses keyword matching to detect complexity.
        """
        desc_lower = description.lower()

        # Check for simple task indicators
        for keyword in _SIMPLE_TASK_KEYWORDS:
            if keyword in desc_lower:
                return False

        # Check for complex task indicators
        complex_score = sum(1 for keyword in _COMPLEX_TASK_KEYWORDS if keyword in desc_lower)

        # Require at least 2 complex keywords or specific patterns
        if complex_score >= 2:
            return True

        # Check for multi-step patterns
        multi_step_patterns = [
            "and then",
            "followed by",
            "after that",
            "step by step",
        ]
        for pattern in multi_step_patterns:
            if pattern in desc_lower:
                return True

        return False

    def _extract_task_description(self, tool_call: dict) -> str:
        """Extract task description from tool call arguments."""
        args = tool_call.get("args", {})

        # Try common description fields
        for field in ["description", "prompt", "task", "goal", "query"]:
            if field in args:
                return str(args[field])

        # Fallback: use all args
        return str(args)

    def _get_tenant_id(self) -> str:
        """Extract tenant ID from current context."""
        tenant = get_current_tenant()
        return tenant.id if tenant else "default"

    def _get_thread_id(self) -> str:
        """Extract thread ID from current context."""
        # This would be set by the runtime
        return "default_thread"

    async def _execute_with_agent_team(
        self,
        task_description: str,
    ) -> str:
        """Execute task using Agent Teams.

        Args:
            task_description: The task to execute

        Returns:
            Aggregated result from Agent Team execution
        """
        decomposer = self._get_decomposer()
        orchestrator = self._get_orchestrator()

        tenant_id = self._get_tenant_id()
        thread_id = self._get_thread_id()

        # Decompose task
        logger.info("Decomposing task for Agent Team: tenant=%s, thread=%s", tenant_id, thread_id)

        plan = await decomposer.decompose(
            goal=task_description,
            context={},
        )

        if not plan.tasks:
            logger.warning("Task decomposition returned no tasks")
            return "Task could not be decomposed into sub-tasks."

        logger.info("Executing plan with %d tasks: %s", len(plan.tasks), plan.parallel_groups)

        # Execute plan
        result = await orchestrator.execute_plan(
            plan=plan,
            thread_id=thread_id,
            tenant_id=tenant_id,
        )

        logger.info("Agent Team execution complete: success=%d, failed=%d", result.success_count, result.failure_count)

        return result.aggregated_output

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        """Wrap tool call with Agent Team routing."""
        if not self.enabled:
            return handler(request)

        tool_call = request.tool_call
        tool_name = tool_call.get("name", "")

        # Only process 'task' tool
        if tool_name != "task":
            return handler(request)

        # Extract task description
        task_description = self._extract_task_description(tool_call)

        # Check if complex enough for Agent Teams
        if not self._is_complex_task(task_description):
            logger.debug("Task not complex enough for Agent Team: %s", task_description[:50])
            return handler(request)

        logger.info("Routing complex task to Agent Team: %s", task_description[:50])

        try:
            # Execute with Agent Teams
            import asyncio

            result = asyncio.run(self._execute_with_agent_team(task_description))

            return ToolMessage(
                content=result,
                tool_call_id=str(tool_call.get("id") or "missing_id"),
                name=tool_name,
            )
        except Exception as e:
            logger.error("Agent Team execution failed: %s. Falling back to default handler.", e)
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

        # Only process 'task' tool
        if tool_name != "task":
            return await handler(request)

        # Extract task description
        task_description = self._extract_task_description(tool_call)

        # Check if complex enough for Agent Teams
        if not self._is_complex_task(task_description):
            logger.debug("Task not complex enough for Agent Team (async): %s", task_description[:50])
            return await handler(request)

        logger.info("Routing complex task to Agent Team (async): %s", task_description[:50])

        try:
            # Execute with Agent Teams
            result = await self._execute_with_agent_team(task_description)

            return ToolMessage(
                content=result,
                tool_call_id=str(tool_call.get("id") or "missing_id"),
                name=tool_name,
            )
        except Exception as e:
            logger.error("Agent Team execution failed (async): %s. Falling back.", e)
            return await handler(request)
