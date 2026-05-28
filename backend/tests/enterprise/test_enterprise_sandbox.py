"""Tests for EnterpriseSandboxProvider and AuditedSandbox."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from deerflow.enterprise.enterprise_sandbox import (
    AuditedSandbox,
    AuditSandboxEventType,
    EnterpriseSandboxProvider,
)


class TestAuditSandboxEventType:
    def test_event_types_exist(self):
        """Should have all required event types."""
        assert AuditSandboxEventType.SANDBOX_ACQUIRED.value == "sandbox.acquired"
        assert AuditSandboxEventType.SANDBOX_RELEASED.value == "sandbox.released"
        assert AuditSandboxEventType.COMMAND_EXECUTED.value == "command.executed"
        assert AuditSandboxEventType.FILE_READ.value == "file.read"
        assert AuditSandboxEventType.FILE_WRITTEN.value == "file.written"
        assert AuditSandboxEventType.NETWORK_REQUEST.value == "network.request"
        assert AuditSandboxEventType.RESOURCE_LIMIT.value == "resource.limit_exceeded"


class TestEnterpriseSandboxProvider:
    @pytest.fixture
    def mock_base_provider(self):
        """Create a mock base sandbox provider."""
        provider = Mock()
        sandbox = Mock()
        sandbox.id = "sandbox_123"
        sandbox.tenant_id = "tenant_abc"
        provider.acquire = AsyncMock(return_value=sandbox)
        provider.get = AsyncMock(return_value=sandbox)
        provider.release = AsyncMock()
        return provider

    @pytest.fixture
    def mock_audit_log(self):
        """Create a mock audit log."""
        audit = Mock()
        audit.log = AsyncMock()
        return audit

    @pytest.fixture
    def mock_quota_manager(self):
        """Create a mock quota manager."""
        quota = Mock()
        quota.check_before_acquire = AsyncMock()
        return quota

    @pytest.fixture
    def provider(self, mock_base_provider, mock_audit_log, mock_quota_manager):
        """Create an EnterpriseSandboxProvider with mocks."""
        return EnterpriseSandboxProvider(
            base_provider=mock_base_provider,
            audit_log=mock_audit_log,
            quota_manager=mock_quota_manager,
        )

    @pytest.mark.asyncio
    async def test_acquire_checks_quota(self, provider, mock_quota_manager):
        """Should check quota before acquiring sandbox."""
        await provider.acquire("thread_1", "tenant_abc")
        mock_quota_manager.check_before_acquire.assert_called_once_with("tenant_abc")

    @pytest.mark.asyncio
    async def test_acquire_logs_audit_event(self, provider, mock_audit_log):
        """Should log sandbox acquired event."""
        await provider.acquire("thread_1", "tenant_abc")
        mock_audit_log.log.assert_called_once()
        call_args = mock_audit_log.log.call_args
        assert call_args[0][0] == AuditSandboxEventType.SANDBOX_ACQUIRED

    @pytest.mark.asyncio
    async def test_acquire_returns_audited_sandbox(self, provider):
        """Should return AuditedSandbox wrapper."""
        result = await provider.acquire("thread_1", "tenant_abc")
        assert isinstance(result, AuditedSandbox)

    @pytest.mark.asyncio
    async def test_get_returns_audited_sandbox(self, provider):
        """Should return AuditedSandbox for get operation."""
        result = await provider.get("sandbox_123", "tenant_abc")
        assert isinstance(result, AuditedSandbox)

    @pytest.mark.asyncio
    async def test_release_logs_event(self, provider, mock_base_provider, mock_audit_log):
        """Should log sandbox released event."""
        await provider.release("sandbox_123", "tenant_abc")
        mock_audit_log.log.assert_called_once()
        call_args = mock_audit_log.log.call_args
        assert call_args[0][0] == AuditSandboxEventType.SANDBOX_RELEASED

    @pytest.mark.asyncio
    async def test_acquire_passes_through_base(self, provider, mock_base_provider):
        """Should call base provider with correct arguments."""
        await provider.acquire("thread_1", "tenant_abc")
        mock_base_provider.acquire.assert_called_once_with("thread_1", "tenant_abc")

    @pytest.mark.asyncio
    async def test_quota_exceeded_raises(self, provider, mock_quota_manager):
        """Should raise when quota exceeded."""
        mock_quota_manager.check_before_acquire.side_effect = Exception("Quota exceeded")
        with pytest.raises(Exception, match="Quota exceeded"):
            await provider.acquire("thread_1", "tenant_abc")


class TestAuditedSandbox:
    @pytest.fixture
    def mock_sandbox(self):
        """Create a mock sandbox."""
        sandbox = Mock()
        sandbox.id = "sandbox_123"
        sandbox.tenant_id = "tenant_abc"
        sandbox.thread_id = "thread_1"
        sandbox.execute_command = AsyncMock(return_value={"output": "result", "exit_code": 0})
        sandbox.read_file = AsyncMock(return_value="file content")
        sandbox.write_file = AsyncMock()
        sandbox.list_dir = AsyncMock(return_value=["file1.txt", "dir1/"])
        return sandbox

    @pytest.fixture
    def mock_audit_log(self):
        """Create a mock audit log."""
        audit = Mock()
        audit.log = AsyncMock()
        return audit

    @pytest.fixture
    def audited_sandbox(self, mock_sandbox, mock_audit_log):
        """Create an AuditedSandbox wrapper."""
        return AuditedSandbox(
            sandbox=mock_sandbox,
            audit_log=mock_audit_log,
        )

    @pytest.mark.asyncio
    async def test_execute_command_logs_event(self, audited_sandbox, mock_audit_log):
        """Should log command execution."""
        await audited_sandbox.execute_command("ls -la", timeout=60)
        mock_audit_log.log.assert_called_once()
        call_args = mock_audit_log.log.call_args
        assert call_args[0][0] == AuditSandboxEventType.COMMAND_EXECUTED

    @pytest.mark.asyncio
    async def test_execute_command_passes_through(self, audited_sandbox, mock_sandbox):
        """Should return base sandbox result."""
        result = await audited_sandbox.execute_command("ls -la")
        assert result == {"output": "result", "exit_code": 0}
        mock_sandbox.execute_command.assert_called_once_with("ls -la", None)

    @pytest.mark.asyncio
    async def test_read_file_logs_event(self, audited_sandbox, mock_audit_log):
        """Should log file read operation."""
        await audited_sandbox.read_file("/path/to/file.txt")
        mock_audit_log.log.assert_called_once()
        call_args = mock_audit_log.log.call_args
        assert call_args[0][0] == AuditSandboxEventType.FILE_READ

    @pytest.mark.asyncio
    async def test_write_file_logs_event(self, audited_sandbox, mock_audit_log):
        """Should log file write operation."""
        await audited_sandbox.write_file("/path/to/file.txt", "content")
        mock_audit_log.log.assert_called_once()
        call_args = mock_audit_log.log.call_args
        assert call_args[0][0] == AuditSandboxEventType.FILE_WRITTEN

    @pytest.mark.asyncio
    async def test_list_dir_logs_event(self, audited_sandbox, mock_audit_log):
        """Should log directory listing."""
        await audited_sandbox.list_dir("/path/to/dir")
        mock_audit_log.log.assert_called_once()
        call_args = mock_audit_log.log.call_args
        assert call_args[0][0] == AuditSandboxEventType.FILE_READ

    @pytest.mark.asyncio
    async def test_audit_event_includes_context(self, audited_sandbox, mock_audit_log):
        """Should include tenant/thread context in audit events."""
        await audited_sandbox.execute_command("echo test")
        call_kwargs = mock_audit_log.log.call_args[1]
        assert "details" in call_kwargs
        assert call_kwargs["details"]["sandbox_id"] == "sandbox_123"
        assert call_kwargs["details"]["tenant_id"] == "tenant_abc"
        assert call_kwargs["details"]["thread_id"] == "thread_1"

    def test_properties_passed_through(self, audited_sandbox, mock_sandbox):
        """Should expose sandbox properties."""
        assert audited_sandbox.id == "sandbox_123"
        assert audited_sandbox.tenant_id == "tenant_abc"
        assert audited_sandbox.thread_id == "thread_1"

    @pytest.mark.asyncio
    async def test_network_request_logs_event(self, audited_sandbox, mock_sandbox, mock_audit_log):
        """Should log network requests if sandbox has network capability."""
        mock_sandbox.network_request = AsyncMock(return_value={"status": 200})
        await audited_sandbox.network_request("https://example.com")
        mock_audit_log.log.assert_called_once()
        call_args = mock_audit_log.log.call_args
        assert call_args[0][0] == AuditSandboxEventType.NETWORK_REQUEST
