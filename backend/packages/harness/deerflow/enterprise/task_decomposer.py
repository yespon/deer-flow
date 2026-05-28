"""Task decomposition for Agent Teams.

Provides LLM-driven task decomposition to break complex goals into
sub-tasks that can be assigned to specialized agents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from deerflow.subagents.config import SubagentConfig
from deerflow.subagents.registry import get_subagent_config, get_subagent_names


@dataclass
class SubTask:
    """A single sub-task within an execution plan.

    Attributes:
        id: Unique task identifier
        description: Task description/prompt for the agent
        agent_type: Type of agent to execute this task
        dependencies: List of task IDs that must complete before this task
        estimated_tokens: Estimated token usage for this task
        timeout_seconds: Maximum execution time
    """

    id: str
    description: str
    agent_type: str
    dependencies: list[str] = field(default_factory=list)
    estimated_tokens: int = 0
    timeout_seconds: int = 300


@dataclass
class ExecutionPlan:
    """A decomposition plan containing multiple sub-tasks.

    Attributes:
        goal: The original high-level goal
        tasks: List of sub-tasks to execute
        parallel_groups: Groups of tasks that can execute in parallel
    """

    goal: str
    tasks: list[SubTask] = field(default_factory=list)

    @property
    def parallel_groups(self) -> list[list[str]]:
        """Group tasks by dependency level for parallel execution.

        Returns groups of task IDs where each group has no dependencies
        on tasks within the same group.
        """
        if not self.tasks:
            return []

        # Build dependency graph
        completed = set()
        remaining = {t.id: t for t in self.tasks}
        groups = []

        while remaining:
            # Find tasks with all dependencies satisfied
            group = []
            for task_id, task in list(remaining.items()):
                if all(dep in completed for dep in task.dependencies):
                    group.append(task_id)

            if not group:
                # Circular dependency detected
                raise ValueError("Circular dependency detected in task graph")

            groups.append(group)
            for task_id in group:
                completed.add(task_id)
                del remaining[task_id]

        return groups

    def get_task(self, task_id: str) -> SubTask | None:
        """Get task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None


class TaskDecomposer:
    """LLM-driven task decomposer for Agent Teams.

    Breaks down complex goals into executable sub-tasks.
    """

    def __init__(self, llm_client: Any | None = None) -> None:
        """Initialize the decomposer.

        Args:
            llm_client: LLM client for decomposition (optional, can use default)
        """
        self.llm_client = llm_client

    async def decompose(
        self,
        goal: str,
        context: dict[str, Any],
        available_agents: list[str] | None = None,
    ) -> ExecutionPlan:
        """Decompose a goal into sub-tasks.

        Args:
            goal: The high-level goal to achieve
            context: Additional context (conversation history, files, etc.)
            available_agents: List of available agent types (auto-detect if None)

        Returns:
            ExecutionPlan containing sub-tasks
        """
        # Auto-detect available agents if not specified
        if available_agents is None:
            available_agents = self._get_available_agent_types()

        # Build decomposition prompt
        prompt = self._build_decomposition_prompt(goal, context, available_agents)

        # Call LLM to decompose
        if self.llm_client is not None:
            decomposition = await self._llm_decompose(prompt)
        else:
            # Fallback: simple heuristic decomposition
            decomposition = self._heuristic_decompose(goal, available_agents)

        # Build execution plan
        plan = self._build_plan(goal, decomposition)

        return plan

    def _get_available_agent_types(self) -> list[str]:
        """Get list of available agent types from registry."""
        return get_subagent_names()

    def _build_decomposition_prompt(
        self,
        goal: str,
        context: dict[str, Any],
        available_agents: list[str],
    ) -> str:
        """Build prompt for LLM decomposition."""
        agents_info = "\n".join(
            f"- {name}: {self._get_agent_description(name)}"
            for name in available_agents
        )

        return f"""Decompose the following goal into sub-tasks that can be executed by specialized agents.

Goal: {goal}

Available Agent Types:
{agents_info}

Context:
{context}

Provide a decomposition in the following format:
1. Task ID: <unique_id>
   Agent: <agent_type>
   Description: <detailed description>
   Dependencies: <comma-separated task IDs or "none">

Ensure:
- Each task is assigned to the most appropriate agent type
- Dependencies are clearly specified
- Tasks are granular enough to be executed independently"""

    def _get_agent_description(self, name: str) -> str:
        """Get description for an agent type."""
        config = get_subagent_config(name)
        if config:
            return config.description
        return "Custom agent"

    async def _llm_decompose(self, prompt: str) -> list[dict[str, Any]]:
        """Use LLM to decompose task."""
        # This would call the LLM - simplified for now
        # Return placeholder structure
        return []

    def _heuristic_decompose(
        self,
        goal: str,
        available_agents: list[str],
    ) -> list[dict[str, Any]]:
        """Simple heuristic decomposition when LLM is unavailable.

        This is a fallback that creates a single task for the general-purpose agent.
        """
        return [
            {
                "id": "task_1",
                "agent_type": "general-purpose",
                "description": goal,
                "dependencies": [],
            }
        ]

    def _build_plan(self, goal: str, decomposition: list[dict[str, Any]]) -> ExecutionPlan:
        """Build ExecutionPlan from decomposition."""
        tasks = []
        for item in decomposition:
            task = SubTask(
                id=item["id"],
                description=item["description"],
                agent_type=item["agent_type"],
                dependencies=item.get("dependencies", []),
            )
            tasks.append(task)

        return ExecutionPlan(goal=goal, tasks=tasks)
