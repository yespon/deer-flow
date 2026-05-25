"""Tests for approval workflow."""
import pytest
from deerflow.enterprise.approval import (
    ApprovalRequest,
    ApprovalRule,
    ApprovalRuleEngine,
    ApprovalStatus,
    get_approval_engine,
)


class TestApprovalRule:
    def test_rule_creation(self):
        rule = ApprovalRule(
            name="test_rule",
            condition=lambda tc: True,
            approvers=["admin"],
            timeout_hours=4,
        )
        assert rule.name == "test_rule"
        assert rule.timeout_hours == 4


class TestApprovalRequest:
    def test_request_creation(self):
        req = ApprovalRequest(
            request_id="req_1",
            rule_name="test",
            tenant_id="t1",
            thread_id="th1",
            tool_call={"tool": "test"},
        )
        assert req.status == ApprovalStatus.PENDING


class TestApprovalRuleEngine:
    def test_engine_initialization(self):
        engine = ApprovalRuleEngine()
        rule = engine.get_rule("financial_transaction")
        assert rule is not None
        assert "cfo" in rule.approvers

    def test_register_rule(self):
        engine = ApprovalRuleEngine()
        rule = ApprovalRule(
            name="custom",
            condition=lambda tc: tc.get("x") > 5,
            approvers=["manager"],
        )
        engine.register_rule(rule)
        assert engine.get_rule("custom") == rule

    def test_check_rules(self):
        engine = ApprovalRuleEngine()
        matches = engine.check_rules({"amount": 20000})
        assert any(r.name == "financial_transaction" for r in matches)

    def test_create_and_approve_request(self):
        engine = ApprovalRuleEngine()
        req = engine.create_request(
            rule_name="financial_transaction",
            tenant_id="t1",
            thread_id="th1",
            tool_call={"amount": 15000},
        )
        assert req.status == ApprovalStatus.PENDING
        engine.approve(req.request_id, "finance_manager")
        assert req.status == ApprovalStatus.APPROVED

    def test_reject_request(self):
        engine = ApprovalRuleEngine()
        req = engine.create_request(
            rule_name="financial_transaction",
            tenant_id="t1",
            thread_id="th1",
            tool_call={},
        )
        engine.reject(req.request_id, "finance_manager")
        assert req.status == ApprovalStatus.REJECTED


class TestGlobalEngine:
    def test_get_approval_engine(self):
        e1 = get_approval_engine()
        e2 = get_approval_engine()
        assert e1 is e2
