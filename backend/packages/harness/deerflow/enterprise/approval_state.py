"""Approval state persistence for Human-in-Loop.

Manages suspended execution states and approval workflow persistence.
"""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from deerflow.enterprise.approval import ApprovalRequest, ApprovalStatus, get_approval_engine


@dataclass
class SuspendedState:
    """A suspended execution state waiting for approval."""
    thread_id: str
    checkpoint: dict[str, Any]
    approval: ApprovalRequest
    suspended_at: datetime


class ApprovalStateManager:
    """Manages persistence of approval states and suspended executions."""

    def __init__(self, storage_path: str = ".deer-flow/approvals") -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def suspend_execution(
        self,
        thread_id: str,
        checkpoint: dict[str, Any],
        approval: ApprovalRequest,
    ) -> SuspendedState:
        """Suspend execution and save state."""
        state = SuspendedState(
            thread_id=thread_id,
            checkpoint=checkpoint,
            approval=approval,
            suspended_at=datetime.utcnow(),
        )

        # Save to file
        state_file = self.storage_path / f"{approval.request_id}.json"
        with open(state_file, "w") as f:
            json.dump(self._state_to_dict(state), f, indent=2)

        return state

    def resume_execution(
        self,
        approval_id: str,
    ) -> SuspendedState | None:
        """Resume a suspended execution."""
        state_file = self.storage_path / f"{approval_id}.json"

        if not state_file.exists():
            return None

        with open(state_file, "r") as f:
            data = json.load(f)

        return self._dict_to_state(data)

    def delete_state(self, approval_id: str) -> bool:
        """Delete a suspended state."""
        state_file = self.storage_path / f"{approval_id}.json"
        if state_file.exists():
            state_file.unlink()
            return True
        return False

    def list_pending(self, tenant_id: str | None = None) -> list[SuspendedState]:
        """List all pending suspended states."""
        states = []
        for state_file in self.storage_path.glob("*.json"):
            with open(state_file, "r") as f:
                data = json.load(f)
            state = self._dict_to_state(data)
            if state.approval.status == ApprovalStatus.PENDING:
                if tenant_id is None or state.approval.tenant_id == tenant_id:
                    states.append(state)
        return states

    def _state_to_dict(self, state: SuspendedState) -> dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "thread_id": state.thread_id,
            "checkpoint": state.checkpoint,
            "approval": {
                "request_id": state.approval.request_id,
                "rule_name": state.approval.rule_name,
                "tenant_id": state.approval.tenant_id,
                "thread_id": state.approval.thread_id,
                "tool_call": state.approval.tool_call,
                "status": state.approval.status.value,
                "created_at": state.approval.created_at.isoformat(),
                "approver": state.approval.approver,
                "decision_at": state.approval.decision_at.isoformat() if state.approval.decision_at else None,
                "escalation_level": state.approval.escalation_level,
            },
            "suspended_at": state.suspended_at.isoformat(),
        }

    def _dict_to_state(self, data: dict[str, Any]) -> SuspendedState:
        """Convert dictionary to state."""
        approval_data = data["approval"]
        approval = ApprovalRequest(
            request_id=approval_data["request_id"],
            rule_name=approval_data["rule_name"],
            tenant_id=approval_data["tenant_id"],
            thread_id=approval_data["thread_id"],
            tool_call=approval_data["tool_call"],
            status=ApprovalStatus(approval_data["status"]),
            created_at=datetime.fromisoformat(approval_data["created_at"]),
            approver=approval_data.get("approver"),
            decision_at=datetime.fromisoformat(approval_data["decision_at"]) if approval_data.get("decision_at") else None,
            escalation_level=approval_data.get("escalation_level", 0),
        )

        return SuspendedState(
            thread_id=data["thread_id"],
            checkpoint=data["checkpoint"],
            approval=approval,
            suspended_at=datetime.fromisoformat(data["suspended_at"]),
        )


# Global instance
_global_manager: ApprovalStateManager | None = None


def get_state_manager() -> ApprovalStateManager:
    """Get global approval state manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = ApprovalStateManager()
    return _global_manager
