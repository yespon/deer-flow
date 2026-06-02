"""Hooks fired before summarization removes messages from state."""

from __future__ import annotations

from deerflow.agents.memory.message_processing import detect_correction, detect_reinforcement, filter_messages_for_memory
from deerflow.agents.memory.queue import get_memory_queue
from deerflow.agents.middlewares.summarization_middleware import SummarizationEvent
from deerflow.config.memory_config import get_memory_config
from deerflow.runtime.user_context import resolve_runtime_user_id


def _resolve_team_id(runtime: object | None, user_id: str | None) -> str | None:
    """Resolve team_id from runtime context if scope isolation is enabled.

    When ``scope_isolation`` is "scoped" and the user belongs to at least one
    team, we return the first team_id so memory updates can be optionally
    routed to team scope.  For now, conversation updates default to user scope
    (per ``default_write_scope`` config), so team_id is passed as None.
    This helper exists for future expansion when LLM-tagged scope hints
    route facts to team memory automatically.
    """
    config = get_memory_config()
    if config.scope_isolation != "scoped" or not user_id:
        return None
    # Future: inspect runtime.context["team_id"] for explicit scope hints
    return None


def memory_flush_hook(event: SummarizationEvent) -> None:
    """Flush messages about to be summarized into the memory queue."""
    if not get_memory_config().enabled or not event.thread_id:
        return

    filtered_messages = filter_messages_for_memory(list(event.messages_to_summarize))
    user_messages = [message for message in filtered_messages if getattr(message, "type", None) == "human"]
    assistant_messages = [message for message in filtered_messages if getattr(message, "type", None) == "ai"]
    if not user_messages or not assistant_messages:
        return

    correction_detected = detect_correction(filtered_messages)
    reinforcement_detected = not correction_detected and detect_reinforcement(filtered_messages)
    user_id = resolve_runtime_user_id(event.runtime)
    team_id = _resolve_team_id(event.runtime, user_id)
    queue = get_memory_queue()
    queue.add_nowait(
        thread_id=event.thread_id,
        messages=filtered_messages,
        agent_name=event.agent_name,
        user_id=user_id,
        team_id=team_id,
        correction_detected=correction_detected,
        reinforcement_detected=reinforcement_detected,
    )
