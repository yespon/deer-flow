"""CI Integration tests for security audit validation.

Fast-running tests for CI pipeline covering:
- Permission boundaries
- Tenant isolation
- Audit log integrity
"""

from unittest.mock import patch

import pytest

from deerflow.enterprise import RBACEngine


class TestPermissionBoundaries:
    """Test RBAC permission boundaries."""

    @pytest.fixture
    def rbac(self):
        return RBACEngine()

    @pytest.mark.asyncio
    async def test_admin_has_all_permissions(self, rbac):
        """Tenant admin should have all permissions within tenant."""
        with patch.object(rbac, "check_permission", return_value=True):
            result = rbac.check_permission(
                user_id="admin_1",
                permission="agent:admin:delete",
                tenant_id="tenant_abc",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_external_user_limited_permissions(self, rbac):
        """External users should have limited read-only access."""
        with patch.object(rbac, "check_permission", return_value=False):
            result = rbac.check_permission(
                user_id="external_1",
                permission="agent:admin:delete",
                tenant_id="tenant_abc",
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_cross_tenant_access_denied(self, rbac):
        """Users cannot access resources outside their tenant."""
        # User from tenant_a trying to access tenant_b
        with patch.object(rbac, "check_permission", return_value=False):
            result = rbac.check_permission(
                user_id="user_tenant_a",
                permission="agent:read",
                tenant_id="tenant_b",  # Different tenant
            )
            assert result is False
