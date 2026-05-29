"""Tests for AgentRegistry."""

from deerflow.enterprise.agent_registry import (
    AgentRegistry,
    AgentType,
    get_agent_registry,
)


class TestAgentType:
    def test_agent_type_creation(self):
        agent = AgentType(
            name="test-agent",
            description="Test agent",
            capabilities=["coding", "debugging"],
            specialization_score=0.9,
        )
        assert agent.name == "test-agent"
        assert agent.specialization_score == 0.9

    def test_matches_requirement(self):
        agent = AgentType(
            name="code-agent",
            description="Code agent",
            capabilities=["coding", "debugging"],
        )
        assert agent.matches_requirement("coding")
        assert agent.matches_requirement("debug")
        assert not agent.matches_requirement("research")


class TestAgentRegistry:
    def test_registry_initialization(self):
        registry = AgentRegistry()
        types = registry.list_agent_types()
        assert len(types) > 0
        assert any(t.name == "general-purpose" for t in types)

    def test_register_agent_type(self):
        registry = AgentRegistry()
        agent = AgentType(name="custom", description="Custom agent")
        registry.register_agent_type(agent)
        assert registry.get_agent_type("custom") == agent

    def test_find_agents_by_capability(self):
        registry = AgentRegistry()
        agents = registry.find_agents_by_capability("research")
        assert len(agents) > 0
        assert any(a.name == "research" for a in agents)

    def test_select_best_agent_for_research(self):
        registry = AgentRegistry()
        agent = registry.select_best_agent("Research this topic on the web")
        assert agent is not None
        assert agent.name == "research"

    def test_select_best_agent_for_code(self):
        registry = AgentRegistry()
        agent = registry.select_best_agent("Write a Python function")
        assert agent is not None
        assert agent.name == "code"

    def test_create_instance(self):
        registry = AgentRegistry()
        instance = registry.create_instance("general-purpose", "instance_1")
        assert instance.instance_id == "instance_1"
        assert instance.agent_type == "general-purpose"
        assert instance.status == "idle"

    def test_update_instance_status(self):
        registry = AgentRegistry()
        instance = registry.create_instance("general-purpose", "instance_1")
        registry.update_instance_status("instance_1", "completed", tokens=100)
        assert instance.status == "completed"
        assert instance.task_count == 1
        assert instance.total_tokens == 100


class TestGlobalRegistry:
    def test_get_agent_registry_returns_same_instance(self):
        reg1 = get_agent_registry()
        reg2 = get_agent_registry()
        assert reg1 is reg2
