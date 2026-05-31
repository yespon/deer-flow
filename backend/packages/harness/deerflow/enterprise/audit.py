"""Immutable audit logging with Ed25519 signatures."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric import ed25519


class AuditEventType(StrEnum):
    SANDBOX_ACQUIRED = "sandbox.acquired"
    SANDBOX_RELEASED = "sandbox.released"
    COMMAND_EXECUTED = "command.executed"
    FILE_READ = "file.read"
    FILE_WRITTEN = "file.written"
    NETWORK_REQUEST = "network.request"
    RESOURCE_LIMIT = "resource.limit_exceeded"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    PERMISSION_DENIED = "permission.denied"
    AGENT_CREATED = "agent.created"
    AGENT_EXECUTED = "agent.executed"
    SUBAGENT_SPAWNED = "subagent.spawned"


@dataclass
class AuditEvent:
    event_type: AuditEventType
    tenant_id: str
    thread_id: str
    sandbox_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    previous_hash: str = ""
    signature: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["timestamp"] = self.timestamp.isoformat()
        return data

    def to_signing_bytes(self) -> bytes:
        data = self.to_dict()
        data.pop("signature", None)
        return json.dumps(data, sort_keys=True).encode()

    @property
    def hash(self) -> str:
        return hashlib.sha256(self.to_signing_bytes()).hexdigest()


class AuditSigner:
    def __init__(self, private_key: ed25519.Ed25519PrivateKey | None = None) -> None:
        self._private_key = private_key or ed25519.Ed25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()

    @classmethod
    def generate(cls) -> AuditSigner:
        return cls()

    def sign(self, message: bytes) -> bytes:
        return self._private_key.sign(message)

    def verify(self, message: bytes, signature: bytes) -> bool:
        try:
            self._public_key.verify(signature, message)
            return True
        except Exception:
            return False

    def sign_event(self, event: AuditEvent) -> None:
        message = event.to_signing_bytes()
        signature = self.sign(message)
        event.signature = signature.hex()

    def verify_event(self, event: AuditEvent) -> bool:
        if not event.signature:
            return False
        try:
            signature = bytes.fromhex(event.signature)
            return self.verify(event.to_signing_bytes(), signature)
        except Exception:
            return False


class ImmutableAuditLog:
    def __init__(self, log_path: str, signer: AuditSigner | None = None) -> None:
        self.log_path = Path(log_path)
        self.signer = signer or AuditSigner.generate()
        self._last_hash: str = ""
        self._ensure_file()

    def _ensure_file(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    def append(self, event: AuditEvent) -> None:
        event.previous_hash = self._last_hash
        self.signer.sign_event(event)
        line = json.dumps(event.to_dict()) + "\n"
        with open(self.log_path, "a") as f:
            f.write(line)
        self._last_hash = event.hash

    def read_all(self) -> list[AuditEvent]:
        events = []
        if not self.log_path.exists():
            return events
        with open(self.log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                events.append(
                    AuditEvent(
                        event_type=AuditEventType(data["event_type"]),
                        tenant_id=data["tenant_id"],
                        thread_id=data["thread_id"],
                        sandbox_id=data.get("sandbox_id", ""),
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        payload=data.get("payload", {}),
                        event_id=data["event_id"],
                        previous_hash=data.get("previous_hash", ""),
                        signature=data.get("signature", ""),
                    )
                )
        return events

    def verify_chain(self) -> bool:
        events = self.read_all()
        previous_hash = ""
        for event in events:
            if not self.signer.verify_event(event):
                return False
            if event.previous_hash != previous_hash:
                return False
            if event.hash != hashlib.sha256(event.to_signing_bytes()).hexdigest():
                return False
            previous_hash = event.hash
        return True
