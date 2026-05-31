def __getattr__(name: str):
    if name == "SubagentConfig":
        from .config import SubagentConfig

        return SubagentConfig
    if name in {"SubagentExecutor", "SubagentResult"}:
        from .executor import SubagentExecutor, SubagentResult

        return {"SubagentExecutor": SubagentExecutor, "SubagentResult": SubagentResult}[name]
    if name in {"get_available_subagent_names", "get_subagent_config", "list_subagents"}:
        from .registry import get_available_subagent_names, get_subagent_config, list_subagents

        return {
            "get_available_subagent_names": get_available_subagent_names,
            "get_subagent_config": get_subagent_config,
            "list_subagents": list_subagents,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "SubagentConfig",
    "SubagentExecutor",
    "SubagentResult",
    "get_available_subagent_names",
    "get_subagent_config",
    "list_subagents",
]
