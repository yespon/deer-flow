"""Approval workflow system for Human-in-Loop.

Provides rule-based approval with state management and notifications.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    TIMEOUT = "timeout"


@dataclass
class ApprovalRule:
    """Rule for triggering approval."""

    name: str
    condition: Callable[[dict[str, Any]], bool]
    approvers: list[str]
    timeout_hours: int = 24
    escalation_chain: list[str] = field(default_factory=list)


@dataclass
class ApprovalRequest:
    """A pending approval request."""

    request_id: str
    rule_name: str
    tenant_id: str
    thread_id: str
    tool_call: dict[str, Any]
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    approver: str | None = None
    decision_at: datetime | None = None
    escalation_level: int = 0

    @property
    def is_expired(self) -> bool:
        if self.status != ApprovalStatus.PENDING:
            return False
        rule = get_rule(self.rule_name)
        if not rule:
            return False
        timeout = timedelta(hours=rule.timeout_hours)
        return datetime.utcnow() > self.created_at + timeout


class ApprovalRuleEngine:
    """Engine for managing approval rules and requests."""

    def __init__(self) -> None:
        self._rules: dict[str, ApprovalRule] = {}
        self._requests: dict[str, ApprovalRequest] = {}
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        """Register default approval rules."""
        self.register_rule(
            ApprovalRule(
                name="financial_transaction",
                condition=lambda tc: tc.get("amount", 0) > 10000,
                approvers=["finance_manager", "cfo"],
                timeout_hours=24,
                escalation_chain=["cfo", "ceo"],
            )
        )
        self.register_rule(
            ApprovalRule(
                name="sensitive_data_access",
                condition=lambda tc: tc.get("tool") in ["query_database", "export_data"],
                approvers=["data_owner"],
                timeout_hours=4,
                escalation_chain=["admin"],
            )
        )

    def register_rule(self, rule: ApprovalRule) -> None:
        """Register an approval rule."""
        self._rules[rule.name] = rule

    def get_rule(self, name: str) -> ApprovalRule | None:
        """Get rule by name."""
        return self._rules.get(name)

    def check_rules(self, tool_call: dict[str, Any]) -> list[ApprovalRule]:
        """Check which rules match a tool call."""
        return [rule for rule in self._rules.values() if rule.condition(tool_call)]

    def create_request(
        self,
        rule_name: str,
        tenant_id: str,
        thread_id: str,
        tool_call: dict[str, Any],
    ) -> ApprovalRequest:
        """Create a new approval request."""
        import uuid

        request = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            rule_name=rule_name,
            tenant_id=tenant_id,
            thread_id=thread_id,
            tool_call=tool_call,
        )
        self._requests[request.request_id] = request
        return request

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        """Get request by ID."""
        return self._requests.get(request_id)

    def approve(self, request_id: str, approver: str) -> ApprovalRequest | None:
        """Approve a request."""
        request = self._requests.get(request_id)
        if request and request.status == ApprovalStatus.PENDING:
            request.status = ApprovalStatus.APPROVED
            request.approver = approver
            request.decision_at = datetime.utcnow()
        return request

    def reject(self, request_id: str, approver: str) -> ApprovalRequest | None:
        """Reject a request."""
        request = self._requests.get(request_id)
        if request and request.status == ApprovalStatus.PENDING:
            request.status = ApprovalStatus.REJECTED
            request.approver = approver
            request.decision_at = datetime.utcnow()
        return request

    def escalate(self, request_id: str) -> ApprovalRequest | None:
        """Escalate a request to next level."""
        request = self._requests.get(request_id)
        if not request:
            return None

        rule = self._rules.get(request.rule_name)
        if not rule or request.escalation_level >= len(rule.escalation_chain):
            return None

        request.escalation_level += 1
        request.status = ApprovalStatus.ESCALATED
        return request

    def get_current_approver(self, request: ApprovalRequest) -> str | None:
        """Get current approver for request."""
        rule = self._rules.get(request.rule_name)
        if not rule:
            return None

        level = min(request.escalation_level, len(rule.approvers) - 1)
        return rule.approvers[level]


# Global engine
_global_engine: ApprovalRuleEngine | None = None


def get_approval_engine() -> ApprovalRuleEngine:
    """Get global approval engine."""
    global _global_engine
    if _global_engine is None:
        _global_engine = ApprovalRuleEngine()
    return _global_engine


def get_rule(name: str) -> ApprovalRule | None:
    """Get rule from global engine."""
    return get_approval_engine().get_rule(name)
