"""Tests for TaskDecomposer."""

import pytest

from deerflow.enterprise.task_decomposer import (
    ExecutionPlan,
    SubTask,
    TaskDecomposer,
)


class TestSubTask:
    def test_subtask_creation(self):
        task = SubTask(
            id="task_1",
            description="Test task",
            agent_type="general-purpose",
            dependencies=["task_0"],
        )
        assert task.id == "task_1"
        assert task.dependencies == ["task_0"]


class TestExecutionPlan:
    def test_empty_plan(self):
        plan = ExecutionPlan(goal="test")
        assert plan.parallel_groups == []

    def test_parallel_groups_no_dependencies(self):
        tasks = [
            SubTask(id="t1", description="d1", agent_type="a"),
            SubTask(id="t2", description="d2", agent_type="a"),
        ]
        plan = ExecutionPlan(goal="test", tasks=tasks)
        groups = plan.parallel_groups
        assert len(groups) == 1
        assert set(groups[0]) == {"t1", "t2"}

    def test_parallel_groups_with_dependencies(self):
        tasks = [
            SubTask(id="t1", description="d1", agent_type="a"),
            SubTask(id="t2", description="d2", agent_type="a", dependencies=["t1"]),
            SubTask(id="t3", description="d3", agent_type="a", dependencies=["t1"]),
        ]
        plan = ExecutionPlan(goal="test", tasks=tasks)
        groups = plan.parallel_groups
        assert len(groups) == 2
        assert groups[0] == ["t1"]
        assert set(groups[1]) == {"t2", "t3"}


class TestTaskDecomposer:
    @pytest.mark.asyncio
    async def test_decompose_returns_plan(self):
        decomposer = TaskDecomposer()
        plan = await decomposer.decompose(
            goal="Test goal",
            context={},
        )
        assert isinstance(plan, ExecutionPlan)
        assert plan.goal == "Test goal"
