"""Scoped memory service: read across global/team/user, merge, and write.

This is the high-level API that consumers should use when they need memory
that accounts for all isolation boundaries.  It replaces the pattern of
calling ``get_memory_data(user_id=...)`` directly in most cases.

Read flow (for prompt injection):
    1. Load global memory (no user_id, no team_id)
    2. Load team memory for each team the user belongs to
    3. Load user memory (user_id)
    4. Merge all with precedence: user > team > global

Write flow (from conversations):
    By default, writes go to user scope only.  Team and global memory
    are managed through explicit API calls or LLM-tagged scope hints.
"""

from __future__ import annotations

import logging
from typing import Any

from deerflow.agents.memory.memory_scope import (
    MemoryScope,
    ScopeDescriptor,
    merge_memories,
)
from deerflow.agents.memory.storage import MemoryStorage, get_memory_storage
from deerflow.agents.memory.team_membership import (
    TeamMembershipStore,
    get_team_membership_store,
)
from deerflow.config.memory_config import get_memory_config

logger = logging.getLogger(__name__)


class ScopedMemoryService:
    """High-level service for reading/writing memory across isolation scopes."""

    def __init__(
        self,
        storage: MemoryStorage | None = None,
        membership: TeamMembershipStore | None = None,
    ) -> None:
        self._storage = storage or get_memory_storage()
        self._membership = membership or get_team_membership_store()

    def read_merged(
        self,
        *,
        user_id: str | None = None,
        agent_name: str | None = None,
        team_id: str | None = None,
    ) -> dict[str, Any]:
        """Read and merge memory from all accessible scopes.

        When *user_id* is provided, the result includes:
          - Global memory
          - All team memories the user belongs to
          - The user's own memory

        When only *team_id* is provided:
          - Global memory
          - The specified team's memory

        When neither is provided:
          - Global memory only

        Args:
            user_id: Optional user ID for user-scoped resolution.
            agent_name: Optional agent name for per-agent memory.
            team_id: Optional explicit team_id (overrides membership lookup).

        Returns:
            Merged memory dict ready for injection or display.
        """
        scope_pairs: list[tuple[ScopeDescriptor, dict[str, Any]]] = []

        # 1. Global
        global_desc = ScopeDescriptor(MemoryScope.GLOBAL)
        global_data = self._storage.load(agent_name)
        if global_data:
            scope_pairs.append((global_desc, global_data))

        # 2. Teams
        if user_id:
            team_ids = self._membership.get_teams_for_user(user_id)
        elif team_id:
            team_ids = [team_id]
        else:
            team_ids = []

        for tid in team_ids:
            team_desc = ScopeDescriptor(MemoryScope.TEAM, team_id=tid)
            team_data = self._storage.load(agent_name, team_id=tid)
            if team_data:
                scope_pairs.append((team_desc, team_data))

        # 3. User
        if user_id:
            user_desc = ScopeDescriptor(MemoryScope.USER, user_id=user_id, agent_name=agent_name)
            user_data = self._storage.load(agent_name, user_id=user_id)
            if user_data:
                scope_pairs.append((user_desc, user_data))

        if not scope_pairs:
            return {}

        config = get_memory_config()
        return merge_memories(scope_pairs, max_facts=config.max_facts)

    def read_scope(
        self,
        scope: MemoryScope,
        *,
        user_id: str | None = None,
        team_id: str | None = None,
        agent_name: str | None = None,
    ) -> dict[str, Any]:
        """Read memory from a single specific scope."""
        return self._storage.load(agent_name, user_id=user_id, team_id=team_id)

    def write_scope(
        self,
        memory_data: dict[str, Any],
        *,
        user_id: str | None = None,
        team_id: str | None = None,
        agent_name: str | None = None,
    ) -> bool:
        """Write memory to a specific scope."""
        return self._storage.save(memory_data, agent_name, user_id=user_id, team_id=team_id)

    def list_accessible_scopes(
        self,
        *,
        user_id: str | None = None,
    ) -> list[ScopeDescriptor]:
        """Return descriptors for all scopes the user can access."""
        scopes: list[ScopeDescriptor] = [ScopeDescriptor(MemoryScope.GLOBAL)]

        if user_id:
            for tid in self._membership.get_teams_for_user(user_id):
                scopes.append(ScopeDescriptor(MemoryScope.TEAM, team_id=tid))
            scopes.append(ScopeDescriptor(MemoryScope.USER, user_id=user_id))

        return scopes


# ── Singleton ──────────────────────────────────────────────────────────

_service: ScopedMemoryService | None = None


def get_scoped_memory_service() -> ScopedMemoryService:
    """Get the scoped memory service singleton."""
    global _service
    if _service is None:
        _service = ScopedMemoryService()
    return _service
