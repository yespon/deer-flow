from .features import Next, Prev, RuntimeFeatures
from .thread_state import SandboxState, ThreadState


def __getattr__(name: str):
    if name == "create_deerflow_agent":
        from .factory import create_deerflow_agent

        return create_deerflow_agent
    if name == "make_lead_agent":
        from .lead_agent import make_lead_agent
        from .lead_agent.prompt import prime_enabled_skills_cache

        prime_enabled_skills_cache()
        return make_lead_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "create_deerflow_agent",
    "RuntimeFeatures",
    "Next",
    "Prev",
    "make_lead_agent",
    "SandboxState",
    "ThreadState",
]
