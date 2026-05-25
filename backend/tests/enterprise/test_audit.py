"""Tests for DeerFlow Enterprise audit module."""

import pytest

from deerflow.enterprise.audit import (
    AuditEvent,
    AuditEventType,
    AuditSigner,
    ImmutableAuditLog,
)


class TestAuditEventType:
    def test_event_types(self):
        assert AuditEventType.SANDBOX_ACQUIRED.value == "sandbox.acquired"
        assert AuditEventType.COMMAND_EXECUTED.value == "command.executed"


class TestAuditEvent:
    def test_event_creation(self):
        event = AuditEvent(
            event_type=AuditEventType.SANDBOX_ACQUIRED,
            tenant_id="tenant_123",
            thread_id="thread_456",
            sandbox_id="sandbox_789",
            payload={"cpu_limit": 2},
        )
        assert event.event_type == AuditEventType.SANDBOX_ACQUIRED
        assert event.tenant_id == "tenant_123"
        assert event.previous_hash == ""
        assert event.signature == ""

    def test_event_to_dict(self):
        event = AuditEvent(
            event_type=AuditEventType.COMMAND_EXECUTED,
            tenant_id="tenant_123",
            thread_id="thread_456",
            sandbox_id="sandbox_789",
            payload={"command": "ls -la"},
        )
        data = event.to_dict()
        assert data["event_type"] == "command.executed"
        assert data["tenant_id"] == "tenant_123"
        assert "timestamp" in data


class TestAuditSigner:
    def test_sign_and_verify(self):
        signer = AuditSigner.generate()
        message = b"test message"
        signature = signer.sign(message)
        assert signer.verify(message, signature)

    def test_verify_invalid_signature(self):
        signer = AuditSigner.generate()
        message = b"test message"
        signature = signer.sign(message)
        assert not signer.verify(b"different message", signature)


class TestImmutableAuditLog:
    @pytest.fixture
    def signer(self):
        return AuditSigner.generate()

    @pytest.fixture
    def audit_log(self, tmp_path, signer):
        log_path = tmp_path / "audit.log"
        return ImmutableAuditLog(str(log_path), signer)

    def test_append_event(self, audit_log):
        event = AuditEvent(
            event_type=AuditEventType.SANDBOX_ACQUIRED,
            tenant_id="tenant_123",
            thread_id="thread_456",
            sandbox_id="sandbox_789",
            payload={},
        )
        audit_log.append(event)
        assert event.signature != ""
        assert event.event_id != ""

    def test_chain_hash_integrity(self, audit_log):
        event1 = AuditEvent(
            event_type=AuditEventType.SANDBOX_ACQUIRED,
            tenant_id="tenant_123",
            thread_id="thread_1",
            sandbox_id="sandbox_1",
            payload={},
        )
        audit_log.append(event1)

        event2 = AuditEvent(
            event_type=AuditEventType.COMMAND_EXECUTED,
            tenant_id="tenant_123",
            thread_id="thread_1",
            sandbox_id="sandbox_1",
            payload={"cmd": "ls"},
        )
        audit_log.append(event2)
        assert event2.previous_hash == event1.hash

    def test_verify_chain(self, audit_log):
        for i in range(3):
            event = AuditEvent(
                event_type=AuditEventType.COMMAND_EXECUTED,
                tenant_id="tenant_123",
                thread_id="thread_1",
                sandbox_id="sandbox_1",
                payload={"index": i},
            )
            audit_log.append(event)
        assert audit_log.verify_chain()
