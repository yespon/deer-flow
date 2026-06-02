"""Team membership store for resolving user → team mappings.

The store answers one question: given a user_id, which teams do they belong to?

Two backends are provided:
  - ``ConfigTeamMembershipStore``: reads membership from a static mapping in
    ``config.yaml`` (suitable for small deployments, testing, and bootstrapping).
  - ``SQLTeamMembershipStore``: reads from a database table (for production
    deployments with dynamic team management).

The store is accessed through ``get_team_membership_store()`` which respects
the ``team_membership.backend`` config key.
"""

from __future__ import annotations

import abc
import json
import logging
import threading
from pathlib import Path
from typing import Any

from deerflow.config.paths import get_paths

logger = logging.getLogger(__name__)


class TeamMembershipStore(abc.ABC):
    """Abstract base class for team membership resolution."""

    @abc.abstractmethod
    def get_teams_for_user(self, user_id: str) -> list[str]:
        """Return the list of team_ids the user belongs to."""

    @abc.abstractmethod
    def get_members_of_team(self, team_id: str) -> list[str]:
        """Return the list of user_ids in a team."""

    @abc.abstractmethod
    def add_member(self, team_id: str, user_id: str) -> None:
        """Add a user to a team."""

    @abc.abstractmethod
    def remove_member(self, team_id: str, user_id: str) -> None:
        """Remove a user from a team."""

    @abc.abstractmethod
    def list_teams(self) -> list[str]:
        """Return all known team IDs."""


class ConfigTeamMembershipStore(TeamMembershipStore):
    """Read-only store backed by config.yaml ``team_membership.teams`` section.

    Config format:
        team_membership:
          backend: config
          teams:
            team_eng:
              members: ["alice", "bob"]
            team_design:
              members: ["charlie", "alice"]
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._teams: dict[str, list[str]] = {}
        for team_id, team_data in self._config.get("teams", {}).items():
            members = team_data.get("members", []) if isinstance(team_data, dict) else []
            self._teams[team_id] = list(members)

    def get_teams_for_user(self, user_id: str) -> list[str]:
        return [tid for tid, members in self._teams.items() if user_id in members]

    def get_members_of_team(self, team_id: str) -> list[str]:
        return list(self._teams.get(team_id, []))

    def add_member(self, team_id: str, user_id: str) -> None:
        raise NotImplementedError("ConfigTeamMembershipStore is read-only; use a database-backed store for mutations")

    def remove_member(self, team_id: str, user_id: str) -> None:
        raise NotImplementedError("ConfigTeamMembershipStore is read-only; use a database-backed store for mutations")

    def list_teams(self) -> list[str]:
        return list(self._teams.keys())


class FileTeamMembershipStore(TeamMembershipStore):
    """JSON-file-backed store for team membership.

    File location: ``{base_dir}/teams/membership.json``

    Format:
        {
          "team_eng": ["alice", "bob"],
          "team_design": ["charlie", "alice"]
        }
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or get_paths().base_dir / "teams" / "membership.json"
        self._lock = threading.Lock()
        self._data: dict[str, list[str]] | None = None

    def _load(self) -> dict[str, list[str]]:
        if self._data is not None:
            return self._data
        if not self._path.exists():
            self._data = {}
            return self._data
        try:
            with open(self._path, encoding="utf-8") as f:
                self._data = json.load(f)
            return self._data  # type: ignore[return-value]
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load team membership file %s: %s", self._path, e)
            self._data = {}
            return self._data

    def _save(self) -> None:
        if self._data is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(f".{threading.get_ident()}.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        tmp.replace(self._path)

    def _invalidate(self) -> None:
        self._data = None

    def get_teams_for_user(self, user_id: str) -> list[str]:
        data = self._load()
        return [tid for tid, members in data.items() if user_id in members]

    def get_members_of_team(self, team_id: str) -> list[str]:
        return list(self._load().get(team_id, []))

    def add_member(self, team_id: str, user_id: str) -> None:
        with self._lock:
            data = self._load()
            members = data.setdefault(team_id, [])
            if user_id not in members:
                members.append(user_id)
            self._save()

    def remove_member(self, team_id: str, user_id: str) -> None:
        with self._lock:
            data = self._load()
            members = data.get(team_id, [])
            if user_id in members:
                members.remove(user_id)
            self._save()

    def list_teams(self) -> list[str]:
        return list(self._load().keys())


# ── Singleton ──────────────────────────────────────────────────────────

_store: TeamMembershipStore | None = None
_store_lock = threading.Lock()


def get_team_membership_store() -> TeamMembershipStore:
    """Get the configured team membership store singleton."""
    global _store
    if _store is not None:
        return _store

    with _store_lock:
        if _store is not None:
            return _store

        # Default: file-backed store
        _store = FileTeamMembershipStore()
        return _store


def set_team_membership_store(store: TeamMembershipStore) -> None:
    """Override the global team membership store (for testing or config-driven init)."""
    global _store
    with _store_lock:
        _store = store
