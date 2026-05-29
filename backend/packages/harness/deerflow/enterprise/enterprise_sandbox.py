"""Enterprise Sandbox Provider with audit and quota integration.

This module provides enterprise-grade sandbox capabilities including:
- Full audit logging of all sandbox operations
- Quota enforcement before resource acquisition
- Immutable audit trail for compliance
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from deerflow.enterprise.audit import AuditEventType
    from deerflow.sandbox.provider import SandboxProvider
    from deerflow.sandbox.sandbox import Sandbox


class AuditSandboxEventType(Enum):
    """Audit event types for sandbox operations."""

    SANDBOX_ACQUIRED = "sandbox.acquired"
    SANDBOX_RELEASED = "sandbox.released"
    COMMAND_EXECUTED = "command.executed"
    FILE_READ = "file.read"
    FILE_WRITTEN = "file.written"
    NETWORK_REQUEST = "network.request"
    RESOURCE_LIMIT = "resource.limit_exceeded"


class AuditLogProtocol(Protocol):
    """Protocol for audit log implementation."""

    async def log(
        self,
        event_type: AuditEventType | AuditSandboxEventType,
        details: dict[str, Any],
    ) -> None:
        """Log an audit event."""
        ...


class QuotaManagerProtocol(Protocol):
    """Protocol for quota manager implementation."""

    async def check_before_acquire(self, tenant_id: str) -> None:
        """Check quota before acquiring sandbox. Raises if quota exceeded."""
        ...


class AuditedSandbox:
    """Wrapper that audits all sandbox operations.

    Wraps a base Sandbox instance and logs all operations to the audit log.
    Preserves the full Sandbox interface while adding audit capabilities.
    """

    def __init__(
        self,
        sandbox: Sandbox,
        audit_log: AuditLogProtocol,
    ) -> None:
        self._sandbox = sandbox
        self._audit_log = audit_log

    def __getattr__(self, name: str) -> Any:
        """Pass through attribute access to wrapped sandbox."""
        return getattr(self._sandbox, name)

    @property
    def id(self) -> str:
        """Sandbox identifier."""
        return self._sandbox.id

    @property
    def tenant_id(self) -> str | None:
        """Tenant identifier if available."""
        return getattr(self._sandbox, "tenant_id", None)

    @property
    def thread_id(self) -> str | None:
        """Thread identifier if available."""
        return getattr(self._sandbox, "thread_id", None)

    async def execute_command(
        self,
        command: str,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Execute command with audit logging."""
        result = await self._sandbox.execute_command(command, timeout)

        await self._audit_log.log(
            AuditSandboxEventType.COMMAND_EXECUTED,
            details={
                "sandbox_id": self.id,
                "tenant_id": self.tenant_id,
                "thread_id": self.thread_id,
                "command": command,
                "timeout": timeout,
                "exit_code": result.get("exit_code"),
            },
        )

        return result

    async def read_file(
        self,
        path: str,
        offset: int | None = None,
        limit: int | None = None,
    ) -> str:
        """Read file with audit logging."""
        content = await self._sandbox.read_file(path, offset, limit)

        await self._audit_log.log(
            AuditSandboxEventType.FILE_READ,
            details={
                "sandbox_id": self.id,
                "tenant_id": self.tenant_id,
                "thread_id": self.thread_id,
                "path": path,
                "offset": offset,
                "limit": limit,
                "content_length": len(content),
            },
        )

        return content

    async def write_file(
        self,
        path: str,
        content: str,
        append: bool = False,
    ) -> None:
        """Write file with audit logging."""
        await self._sandbox.write_file(path, content, append)

        await self._audit_log.log(
            AuditSandboxEventType.FILE_WRITTEN,
            details={
                "sandbox_id": self.id,
                "tenant_id": self.tenant_id,
                "thread_id": self.thread_id,
                "path": path,
                "append": append,
                "content_length": len(content),
            },
        )

    async def list_dir(self, path: str) -> list[str]:
        """List directory with audit logging."""
        entries = await self._sandbox.list_dir(path)

        await self._audit_log.log(
            AuditSandboxEventType.FILE_READ,
            details={
                "sandbox_id": self.id,
                "tenant_id": self.tenant_id,
                "thread_id": self.thread_id,
                "path": path,
                "operation": "list_dir",
                "entries_count": len(entries),
            },
        )

        return entries

    async def network_request(
        self,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> dict[str, Any]:
        """Make network request with audit logging."""
        if not hasattr(self._sandbox, "network_request"):
            raise AttributeError("Sandbox does not support network requests")

        result = await self._sandbox.network_request(url, method, headers, body)

        await self._audit_log.log(
            AuditSandboxEventType.NETWORK_REQUEST,
            details={
                "sandbox_id": self.id,
                "tenant_id": self.tenant_id,
                "thread_id": self.thread_id,
                "url": url,
                "method": method,
                "status": result.get("status"),
            },
        )

        return result


class EnterpriseSandboxProvider:
    """Enterprise-grade sandbox provider with audit and quota enforcement.

    Wraps a base sandbox provider and adds:
    - Quota checking before resource acquisition
    - Full audit logging of sandbox lifecycle and operations
    - Compliance-ready audit trail

    Example:
        ```python
        provider = EnterpriseSandboxProvider(
            base_provider=LocalSandboxProvider(),
            audit_log=ImmutableAuditLog(),
            quota_manager=QuotaManager(),
        )

        sandbox = await provider.acquire("thread_1", "tenant_abc")
        result = await sandbox.execute_command("ls -la")
        await provider.release(sandbox.id, "tenant_abc")
        ```
    """

    def __init__(
        self,
        base_provider: SandboxProvider,
        audit_log: AuditLogProtocol,
        quota_manager: QuotaManagerProtocol | None = None,
    ) -> None:
        self._base = base_provider
        self._audit = audit_log
        self._quota = quota_manager

    async def acquire(self, thread_id: str, tenant_id: str | None = None) -> AuditedSandbox:
        """Acquire sandbox with quota check and audit logging.

        Args:
            thread_id: Thread identifier
            tenant_id: Optional tenant identifier for quota enforcement

        Returns:
            AuditedSandbox wrapper with full audit capabilities

        Raises:
            QuotaExceededError: If tenant quota would be exceeded
        """
        # Check quota before acquiring
        if self._quota and tenant_id:
            await self._quota.check_before_acquire(tenant_id)

        # Acquire from base provider
        sandbox = await self._base.acquire(thread_id, tenant_id)

        # Log acquisition
        await self._audit.log(
            AuditSandboxEventType.SANDBOX_ACQUIRED,
            details={
                "sandbox_id": sandbox.id,
                "tenant_id": tenant_id,
                "thread_id": thread_id,
            },
        )

        # Wrap with audit capabilities
        return AuditedSandbox(sandbox, self._audit)

    async def get(self, sandbox_id: str, tenant_id: str | None = None) -> AuditedSandbox | None:
        """Get existing sandbox by ID.

        Args:
            sandbox_id: Sandbox identifier
            tenant_id: Optional tenant identifier

        Returns:
            AuditedSandbox wrapper or None if not found
        """
        sandbox = await self._base.get(sandbox_id, tenant_id)
        if sandbox is None:
            return None

        return AuditedSandbox(sandbox, self._audit)

    async def release(self, sandbox_id: str, tenant_id: str | None = None) -> None:
        """Release sandbox with audit logging.

        Args:
            sandbox_id: Sandbox identifier
            tenant_id: Optional tenant identifier
        """
        await self._base.release(sandbox_id, tenant_id)

        await self._audit.log(
            AuditSandboxEventType.SANDBOX_RELEASED,
            details={
                "sandbox_id": sandbox_id,
                "tenant_id": tenant_id,
            },
        )
