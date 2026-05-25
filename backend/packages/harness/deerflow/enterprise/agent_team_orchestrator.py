"""Agent Team orchestrator for parallel execution.

Manages execution of sub-tasks across multiple agents with dependency tracking.
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Any

from deerflow.enterprise.agent_registry import AgentInstance, get_agent_registry
from deerflow.enterprise.task_decomposer import ExecutionPlan, SubTask
from deerflow.subagents.executor import SubagentExecutor


@dataclass
class SubTaskResult:
    """Result of a sub-task execution."""
    task_id: str
    status: str  # success, failed, timeout
    output: str = ""
    error: str | None = None
    tokens_used: int = 0
    execution_time_ms: int = 0


@dataclass
class TeamExecutionResult:
    """Result of executing an entire plan."""
    plan: ExecutionPlan
    results: dict[str, SubTaskResult] = field(default_factory=dict)
    aggregated_output: str = ""

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results.values() if r.status == "success")

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self.results.values() if r.status == "failed")


class AgentTeamOrchestrator:
    """Orchestrates parallel execution of sub-tasks across agent teams."""

    def __init__(self, max_parallel: int = 3) -> None:
        self.max_parallel = max_parallel
        self.registry = get_agent_registry()
        self._semaphore = asyncio.Semaphore(max_parallel)

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        thread_id: str,
        tenant_id: str,
    ) -> TeamExecutionResult:
        """Execute an execution plan with parallel task scheduling."""
        result = TeamExecutionResult(plan=plan)

        # Get parallel groups
        groups = plan.parallel_groups

        for group in groups:
            # Execute tasks in this group in parallel
            tasks = [plan.get_task(tid) for tid in group]
            tasks = [t for t in tasks if t is not None]

            # Create agent instances
            instances = []
            for task in tasks:
                agent_type = self.registry.select_best_agent(task.description)
                if agent_type:
                    instance_id = f"{thread_id}_{task.id}"
                    instance = self.registry.create_instance(
                        agent_type.name, instance_id
                    )
                    instances.append((task, instance))

            # Execute in parallel with semaphore
            coros = [
                self._execute_subtask(task, instance, thread_id, tenant_id)
                for task, instance in instances
            ]
            group_results = await asyncio.gather(*coros, return_exceptions=True)

            # Store results
            for (task, _), task_result in zip(instances, group_results):
                if isinstance(task_result, Exception):
                    result.results[task.id] = SubTaskResult(
                        task_id=task.id,
                        status="failed",
                        error=str(task_result),
                    )
                else:
                    result.results[task.id] = task_result

        # Aggregate outputs
        result.aggregated_output = self._aggregate_results(
            plan, result.results
        )

        return result

    async def _execute_subtask(
        self,
        task: SubTask,
        instance: AgentInstance,
        thread_id: str,
        tenant_id: str,
    ) -> SubTaskResult:
        """Execute a single sub-task with resource limiting."""
        async with self._semaphore:
            # Update status
            self.registry.update_instance_status(
                instance.instance_id, "running"
            )

            start_time = asyncio.get_event_loop().time()

            try:
                # Get subagent config
                subagent_config = self.registry.get_subagent_config(
                    instance.agent_type
                )

                if not subagent_config:
                    return SubTaskResult(
                        task_id=task.id,
                        status="failed",
                        error=f"Unknown agent type: {instance.agent_type}",
                    )

                # Execute via SubagentExecutor
                executor = SubagentExecutor()

                # Build prompt from task description
                prompt = task.description

                # Execute
                result = await executor.execute(
                    config=subagent_config,
                    prompt=prompt,
                    thread_id=thread_id,
                    tenant_id=tenant_id,
                )

                execution_time = int(
                    (asyncio.get_event_loop().time() - start_time) * 1000
                )

                # Update instance
                self.registry.update_instance_status(
                    instance.instance_id,
                    "completed",
                    tokens=result.get("tokens_used", 0),
                )

                return SubTaskResult(
                    task_id=task.id,
                    status="success",
                    output=result.get("output", ""),
                    tokens_used=result.get("tokens_used", 0),
                    execution_time_ms=execution_time,
                )

            except Exception as e:
                self.registry.update_instance_status(
                    instance.instance_id, "failed"
                )
                return SubTaskResult(
                    task_id=task.id,
                    status="failed",
                    error=str(e),
                )

    def _aggregate_results(
        self,
        plan: ExecutionPlan,
        results: dict[str, SubTaskResult],
    ) -> str:
        """Aggregate sub-task results into final output."""
        outputs = []
        for task in plan.tasks:
            result = results.get(task.id)
            if result and result.output:
                outputs.append(f"## {task.id}\n{result.output}")
        return "\n\n".join(outputs)
