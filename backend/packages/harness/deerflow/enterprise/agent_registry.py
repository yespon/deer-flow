"""Agent registry for enterprise Agent Teams.

Extends the base subagent registry with enterprise features:
- Agent type definitions with capabilities
- Team-based agent assignment
- Agent performance tracking
"""

from __future__ import annotations

from dataclasses import dataclass, field

from deerflow.subagents.config import SubagentConfig
from deerflow.subagents.registry import get_subagent_config


@dataclass
class AgentType:
    """Defines a specialized agent type for Agent Teams.

    Extends SubagentConfig with enterprise capabilities.

    Attributes:
        name: Unique agent type identifier
        description: Human-readable description
        capabilities: List of capability tags
        specialization_score: 0-1 score for this agent's specialization
        cost_per_1k_tokens: Estimated cost per 1k tokens
        avg_latency_ms: Average response latency
    """

    name: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    specialization_score: float = 0.5
    cost_per_1k_tokens: float = 0.0
    avg_latency_ms: int = 1000

    def matches_requirement(self, requirement: str) -> bool:
        """Check if this agent type matches a capability requirement."""
        req_lower = requirement.lower()
        return any(req_lower in cap.lower() for cap in self.capabilities)


@dataclass
class AgentInstance:
    """A running instance of an agent in a team.

    Attributes:
        instance_id: Unique instance identifier
        agent_type: The agent type
        status: Current status (idle, running, completed, failed)
        task_count: Number of tasks executed
        total_tokens: Total tokens consumed
    """

    instance_id: str
    agent_type: str
    status: str = "idle"
    task_count: int = 0
    total_tokens: int = 0


class AgentRegistry:
    """Registry for managing agent types and instances in Agent Teams."""

    def __init__(self) -> None:
        """Initialize the agent registry."""
        self._agent_types: dict[str, AgentType] = {}
        self._instances: dict[str, AgentInstance] = {}
        self._initialize_builtin_types()

    def _initialize_builtin_types(self) -> None:
        """Register built-in agent types."""
        builtin_types = [
            AgentType(
                name="general-purpose",
                description="General purpose agent for any task",
                capabilities=["general", "reasoning", "planning"],
                specialization_score=0.5,
            ),
            AgentType(
                name="research",
                description="Specialized in web research and information gathering",
                capabilities=["research", "web_search", "summarization"],
                specialization_score=0.9,
            ),
            AgentType(
                name="code",
                description="Specialized in code generation and analysis",
                capabilities=["coding", "debugging", "refactoring"],
                specialization_score=0.9,
            ),
            AgentType(
                name="data-analysis",
                description="Specialized in data processing and analysis",
                capabilities=["data_processing", "visualization", "statistics"],
                specialization_score=0.85,
            ),
            AgentType(
                name="bash",
                description="Command execution specialist",
                capabilities=["bash", "system", "file_operations"],
                specialization_score=0.95,
            ),
        ]
        for agent_type in builtin_types:
            self.register_agent_type(agent_type)

    def register_agent_type(self, agent_type: AgentType) -> None:
        """Register a new agent type."""
        self._agent_types[agent_type.name] = agent_type

    def get_agent_type(self, name: str) -> AgentType | None:
        """Get agent type by name."""
        return self._agent_types.get(name)

    def list_agent_types(self) -> list[AgentType]:
        """List all registered agent types."""
        return list(self._agent_types.values())

    def find_agents_by_capability(self, capability: str) -> list[AgentType]:
        """Find agent types that match a capability requirement."""
        return [agent for agent in self._agent_types.values() if agent.matches_requirement(capability)]

    def select_best_agent(self, task_description: str) -> AgentType | None:
        """Select the best agent type for a given task.

        Simple keyword-based matching - can be enhanced with LLM.
        """
        # Keywords to capabilities mapping
        keyword_map = {
            "search": "research",
            "research": "research",
            "web": "research",
            "code": "coding",
            "programming": "coding",
            "python": "coding",
            "function": "coding",
            "debug": "debugging",
            "data": "data_processing",
            "analyze": "data_processing",
            "bash": "bash",
            "command": "bash",
            "shell": "bash",
        }

        # Find matching capabilities
        task_lower = task_description.lower()
        matched_capabilities = set()
        for keyword, capability in keyword_map.items():
            if keyword in task_lower:
                matched_capabilities.add(capability)

        if not matched_capabilities:
            # Return general-purpose agent
            return self._agent_types.get("general-purpose")

        # Find agents with highest specialization for matched capabilities
        best_agent = None
        best_score = 0.0
        for agent in self._agent_types.values():
            score = sum(agent.specialization_score for cap in matched_capabilities if agent.matches_requirement(cap))
            if score > best_score:
                best_score = score
                best_agent = agent

        return best_agent

    def create_instance(self, agent_type: str, instance_id: str) -> AgentInstance:
        """Create a new agent instance."""
        if agent_type not in self._agent_types:
            raise ValueError(f"Unknown agent type: {agent_type}")

        instance = AgentInstance(
            instance_id=instance_id,
            agent_type=agent_type,
        )
        self._instances[instance_id] = instance
        return instance

    def get_instance(self, instance_id: str) -> AgentInstance | None:
        """Get agent instance by ID."""
        return self._instances.get(instance_id)

    def update_instance_status(
        self,
        instance_id: str,
        status: str,
        tokens: int = 0,
    ) -> None:
        """Update agent instance status."""
        instance = self._instances.get(instance_id)
        if instance:
            instance.status = status
            if status == "completed":
                instance.task_count += 1
            instance.total_tokens += tokens

    def get_subagent_config(self, agent_type: str) -> SubagentConfig | None:
        """Get the underlying subagent configuration."""
        return get_subagent_config(agent_type)


# Global registry instance
_global_registry: AgentRegistry | None = None


def get_agent_registry() -> AgentRegistry:
    """Get or create global agent registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
    return _global_registry
