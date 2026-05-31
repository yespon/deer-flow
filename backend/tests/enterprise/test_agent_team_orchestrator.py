"""Tests for AgentTeamOrchestrator."""

from unittest.mock import patch

import pytest

from deerflow.enterprise.agent_team_orchestrator import (
    AgentTeamOrchestrator,
    SubTaskResult,
    TeamExecutionResult,
)
from deerflow.enterprise.task_decomposer import ExecutionPlan, SubTask


class TestSubTaskResult:
    def test_result_creation(self):
        result = SubTaskResult(
            task_id="task_1",
            status="success",
            output="result",
            tokens_used=100,
            execution_time_ms=500,
        )
        assert result.task_id == "task_1"
        assert result.status == "success"
        assert result.tokens_used == 100


class TestTeamExecutionResult:
    def test_empty_result(self):
        plan = ExecutionPlan(goal="test")
        result = TeamExecutionResult(plan=plan)
        assert result.success_count == 0
        assert result.failure_count == 0

    def test_success_count(self):
        plan = ExecutionPlan(goal="test")
        result = TeamExecutionResult(
            plan=plan,
            results={
                "t1": SubTaskResult(task_id="t1", status="success"),
                "t2": SubTaskResult(task_id="t2", status="failed"),
                "t3": SubTaskResult(task_id="t3", status="success"),
            },
        )
        assert result.success_count == 2
        assert result.failure_count == 1


class TestAgentTeamOrchestrator:
    @pytest.fixture
    def orchestrator(self):
        return AgentTeamOrchestrator(max_parallel=2)

    @pytest.fixture
    def simple_plan(self):
        tasks = [
            SubTask(id="t1", description="Task 1", agent_type="general-purpose"),
            SubTask(id="t2", description="Task 2", agent_type="general-purpose"),
        ]
        return ExecutionPlan(goal="Test goal", tasks=tasks)

    @pytest.mark.asyncio
    async def test_execute_empty_plan(self, orchestrator):
        """Should handle empty plan."""
        plan = ExecutionPlan(goal="empty")
        result = await orchestrator.execute_plan(plan, "thread_1", "tenant_1")

        assert isinstance(result, TeamExecutionResult)
        assert result.success_count == 0
        assert result.aggregated_output == ""

    @pytest.mark.asyncio
    async def test_execute_single_task(self, orchestrator, simple_plan):
        """Should execute a single task plan."""
        with patch.object(orchestrator, "_execute_subtask") as mock_execute:
            mock_execute.return_value = SubTaskResult(
                task_id="t1",
                status="success",
                output="Task 1 result",
            )

            # Use a plan with single task
            plan = ExecutionPlan(
                goal="Test",
                tasks=[SubTask(id="t1", description="Task 1", agent_type="general-purpose")],
            )

            result = await orchestrator.execute_plan(plan, "thread_1", "tenant_1")

            assert result.success_count == 1
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_parallel_execution(self, orchestrator):
        """Should execute independent tasks in parallel."""
        tasks = [
            SubTask(id="t1", description="Task 1", agent_type="general-purpose"),
            SubTask(id="t2", description="Task 2", agent_type="general-purpose"),
            SubTask(id="t3", description="Task 3", agent_type="general-purpose"),
        ]
        plan = ExecutionPlan(goal="Parallel test", tasks=tasks)

        with patch.object(orchestrator, "_execute_subtask") as mock_execute:
            mock_execute.return_value = SubTaskResult(
                task_id="t1",
                status="success",
                output="Result",
            )

            result = await orchestrator.execute_plan(plan, "thread_1", "tenant_1")

            # All 3 tasks should be executed
            assert mock_execute.call_count == 3
            assert result.success_count == 3

    @pytest.mark.asyncio
    async def test_sequential_execution_with_dependencies(self, orchestrator):
        """Should respect task dependencies."""
        tasks = [
            SubTask(id="t1", description="Task 1", agent_type="general-purpose"),
            SubTask(
                id="t2",
                description="Task 2",
                agent_type="general-purpose",
                dependencies=["t1"],
            ),
        ]
        plan = ExecutionPlan(goal="Sequential test", tasks=tasks)

        execution_order = []

        async def mock_execute(task, instance, thread_id, tenant_id):
            execution_order.append(task.id)
            return SubTaskResult(task_id=task.id, status="success", output=f"Result {task.id}")

        with patch.object(orchestrator, "_execute_subtask", side_effect=mock_execute):
            result = await orchestrator.execute_plan(plan, "thread_1", "tenant_1")

            # t1 should execute before t2
            assert execution_order.index("t1") < execution_order.index("t2")
            assert result.success_count == 2

    @pytest.mark.asyncio
    async def test_error_handling(self, orchestrator):
        """Should handle task failures gracefully."""
        tasks = [
            SubTask(id="t1", description="Task 1", agent_type="general-purpose"),
            SubTask(id="t2", description="Task 2", agent_type="general-purpose"),
        ]
        plan = ExecutionPlan(goal="Error test", tasks=tasks)

        async def mock_execute_with_error(task, instance, thread_id, tenant_id):
            if task.id == "t1":
                raise Exception("Task 1 failed")
            return SubTaskResult(task_id=task.id, status="success", output="OK")

        with patch.object(orchestrator, "_execute_subtask", side_effect=mock_execute_with_error):
            result = await orchestrator.execute_plan(plan, "thread_1", "tenant_1")

            assert result.success_count == 1
            assert result.failure_count == 1
            assert result.results["t1"].status == "failed"
            assert "Task 1 failed" in result.results["t1"].error

    @pytest.mark.asyncio
    async def test_max_parallel_limit(self, orchestrator):
        """Should respect max_parallel limit."""
        # Create orchestrator with max_parallel=1
        orchestrator = AgentTeamOrchestrator(max_parallel=1)

        tasks = [
            SubTask(id="t1", description="Task 1", agent_type="general-purpose"),
            SubTask(id="t2", description="Task 2", agent_type="general-purpose"),
        ]
        plan = ExecutionPlan(goal="Limit test", tasks=tasks)

        with patch.object(orchestrator, "_execute_subtask") as mock_execute:
            mock_execute.return_value = SubTaskResult(
                task_id="t1",
                status="success",
                output="Result",
            )

            await orchestrator.execute_plan(plan, "thread_1", "tenant_1")

            # Both tasks should still execute
            assert mock_execute.call_count == 2

    def test_aggregate_results(self, orchestrator):
        """Should aggregate task results."""
        plan = ExecutionPlan(
            goal="Test",
            tasks=[
                SubTask(id="t1", description="D1", agent_type="a"),
                SubTask(id="t2", description="D2", agent_type="a"),
            ],
        )
        results = {
            "t1": SubTaskResult(task_id="t1", status="success", output="Output 1"),
            "t2": SubTaskResult(task_id="t2", status="success", output="Output 2"),
        }

        aggregated = orchestrator._aggregate_results(plan, results)

        assert "t1" in aggregated
        assert "t2" in aggregated
        assert "Output 1" in aggregated
        assert "Output 2" in aggregated

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, orchestrator):
        """Should pass tenant_id to subtask execution."""
        tasks = [
            SubTask(id="t1", description="Task 1", agent_type="general-purpose"),
        ]
        plan = ExecutionPlan(goal="Tenant test", tasks=tasks)

        captured_tenant = None

        async def mock_execute(task, instance, thread_id, tenant_id):
            nonlocal captured_tenant
            captured_tenant = tenant_id
            return SubTaskResult(task_id=task.id, status="success")

        with patch.object(orchestrator, "_execute_subtask", side_effect=mock_execute):
            await orchestrator.execute_plan(plan, "thread_1", "tenant_abc")

            assert captured_tenant == "tenant_abc"
