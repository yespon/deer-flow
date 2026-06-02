"""Memory scope model for three-level isolation: global → team → user.

Each memory record lives in exactly one scope.  When reading for prompt
injection, memories from all reachable scopes are merged with clear
precedence: user > team > global (more specific wins on conflict).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class MemoryScope(StrEnum):
    """Identifies which isolation boundary a memory record belongs to.

    Ordering matters: higher values are more specific and win on merge conflict.
    """

    GLOBAL = "global"
    TEAM = "team"
    USER = "user"

    @property
    def precedence(self) -> int:
        """Higher value = higher priority during merge."""
        return _PRECEDENCE[self]


_PRECEDENCE: dict[MemoryScope, int] = {
    MemoryScope.GLOBAL: 0,
    MemoryScope.TEAM: 1,
    MemoryScope.USER: 2,
}


class ScopeDescriptor:
    """Fully identifies a memory scope boundary.

    Examples:
        ScopeDescriptor(MemoryScope.GLOBAL)          # global memory
        ScopeDescriptor(MemoryScope.TEAM, team_id="team_eng")  # team memory
        ScopeDescriptor(MemoryScope.USER, user_id="alice")     # user memory
        ScopeDescriptor(MemoryScope.USER, user_id="alice", agent_name="coder")  # user+agent
    """

    __slots__ = ("scope", "team_id", "user_id", "agent_name")

    def __init__(
        self,
        scope: MemoryScope,
        *,
        team_id: str | None = None,
        user_id: str | None = None,
        agent_name: str | None = None,
    ) -> None:
        self.scope = scope
        self.team_id = team_id
        self.user_id = user_id
        self.agent_name = agent_name
        self._validate()

    def _validate(self) -> None:
        if self.scope == MemoryScope.TEAM and not self.team_id:
            raise ValueError("TEAM scope requires team_id")
        if self.scope == MemoryScope.USER and not self.user_id:
            raise ValueError("USER scope requires user_id")
        if self.agent_name and self.scope != MemoryScope.USER:
            raise ValueError("agent_name is only valid with USER scope")

    @property
    def precedence(self) -> int:
        """Delegate to the scope's precedence value."""
        return self.scope.precedence

    @property
    def cache_key(self) -> tuple[str, str | None, str | None, str | None]:
        """Stable key for deduplication and caching."""
        return (self.scope.value, self.team_id, self.user_id, self.agent_name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ScopeDescriptor):
            return NotImplemented
        return self.cache_key == other.cache_key

    def __hash__(self) -> int:
        return hash(self.cache_key)

    def __repr__(self) -> str:
        parts = [f"scope={self.scope.value}"]
        if self.team_id:
            parts.append(f"team_id={self.team_id!r}")
        if self.user_id:
            parts.append(f"user_id={self.user_id!r}")
        if self.agent_name:
            parts.append(f"agent_name={self.agent_name!r}")
        return f"ScopeDescriptor({', '.join(parts)})"


def tag_memory_with_scope(
    memory_data: dict[str, Any],
    scope_descriptor: ScopeDescriptor,
) -> dict[str, Any]:
    """Annotate every fact in *memory_data* with its originating scope.

    This is a shallow copy — the original dict is not mutated.
    """
    tagged = {**memory_data}
    facts = memory_data.get("facts", [])
    if facts:
        tagged["facts"] = [{**f, "_scope": scope_descriptor.scope.value, "_scope_origin": scope_descriptor.cache_key} for f in facts]
    tagged["_scope"] = scope_descriptor.scope.value
    return tagged


def merge_memories(
    memories: list[tuple[ScopeDescriptor, dict[str, Any]]],
    *,
    max_facts: int = 100,
) -> dict[str, Any]:
    """Merge memories from multiple scopes into a single view.

    Merge rules:
      - Summary fields (user/history sections): highest-precedence scope wins.
      - Facts: collected from all scopes, deduplicated by casefold content.
        On exact-content collision, the fact from the higher-precedence scope
        wins.  Facts are then sorted by confidence (descending) and truncated
        to *max_facts*.

    Returns a merged memory dict *without* scope tags (ready for injection).
    """
    if not memories:
        return {}

    # Sort by precedence ascending so higher-precedence overwrites lower.
    sorted_memories = sorted(memories, key=lambda pair: pair[0].precedence)

    merged_user: dict[str, Any] = {}
    merged_history: dict[str, Any] = {}
    seen_fact_keys: dict[str, int] = {}  # casefold content → precedence
    all_facts: list[dict[str, Any]] = []

    for descriptor, data in sorted_memories:
        # Merge summary sections — higher precedence overwrites
        for section in ("workContext", "personalContext", "topOfMind"):
            val = data.get("user", {}).get(section, {})
            if val.get("summary"):
                merged_user[section] = val

        for section in ("recentMonths", "earlierContext", "longTermBackground"):
            val = data.get("history", {}).get(section, {})
            if val.get("summary"):
                merged_history[section] = val

        # Merge facts — deduplicate by content
        for fact in data.get("facts", []):
            content = fact.get("content", "")
            key = content.strip().casefold() if isinstance(content, str) else ""
            if not key:
                continue

            prec = descriptor.precedence
            existing_prec = seen_fact_keys.get(key, -1)

            if existing_prec < 0:
                # New fact
                seen_fact_keys[key] = prec
                clean = {k: v for k, v in fact.items() if not k.startswith("_scope")}
                all_facts.append(clean)
            elif prec > existing_prec:
                # Replace with higher-precedence version
                seen_fact_keys[key] = prec
                clean = {k: v for k, v in fact.items() if not k.startswith("_scope")}
                # Remove old version
                all_facts = [f for f in all_facts if f.get("content", "").strip().casefold() != key]
                all_facts.append(clean)
            # else: same or lower precedence, skip

    # Sort facts by confidence and truncate
    all_facts.sort(key=lambda f: f.get("confidence", 0), reverse=True)
    all_facts = all_facts[:max_facts]

    return {
        "version": "1.0",
        "user": merged_user,
        "history": merged_history,
        "facts": all_facts,
    }
