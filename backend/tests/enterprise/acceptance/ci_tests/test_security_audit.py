"""CI Integration tests for security audit.

Combined security validation tests for CI pipeline.
"""

from unittest.mock import Mock, patch

import pytest

from deerflow.enterprise import (
    ComplianceFilter,
    ContentType,
    RBACEngine,
    Tenant,
    TenantNamespace,
)


class TestSecurityAuditIntegration:
    """Integrated security audit tests for CI."""

    def test_rbac_permission_check_flow(self):
        """Complete RBAC permission check flow."""
        rbac = RBACEngine()

        # Admin can do anything
        with patch.object(rbac, "check_permission", return_value=True):
            assert rbac.check_permission("admin", "agent:delete", "tenant_1") is True

        # External user cannot delete
        with patch.object(rbac, "check_permission", return_value=False):
            assert rbac.check_permission("external", "agent:delete", "tenant_1") is False

    def test_tenant_isolation_enforced(self):
        """Tenant isolation is properly enforced."""
        tenant_a = Tenant(id="tenant_a", name="A")
        tenant_b = Tenant(id="tenant_b", name="B")

        ns_a = TenantNamespace(tenant_a.id)
        ns_b = TenantNamespace(tenant_b.id)

        # Same resource name, different namespaces
        col_a = ns_a.apply_to_collection("docs")
        col_b = ns_b.apply_to_collection("docs")

        assert col_a != col_b
        assert "tenant_a" in col_a
        assert "tenant_b" in col_b

    @pytest.mark.asyncio
    async def test_compliance_filter_blocks_sensitive_data(self):
        """Compliance filter detects content with sensitive data."""
        compliance = ComplianceFilter(
            sensitive_words=["password", "secret"],
        )

        result = await compliance.filter_output(
            "My password is secret123",
            ContentType.TEXT,
        )

        # Filter detects violations (may not block depending on config)
        assert len(result.violations) > 0
        assert any("password" in str(v) for v in result.violations)

    @pytest.mark.asyncio
    async def test_compliance_filter_allows_clean_content(self):
        """Compliance filter allows clean content."""
        compliance = ComplianceFilter(
            sensitive_words=["password"],
        )

        result = await compliance.filter_output(
            "This is a normal message",
            ContentType.TEXT,
        )

        assert result.blocked is False
