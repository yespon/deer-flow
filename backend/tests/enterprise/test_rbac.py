"""Tests for DeerFlow Enterprise RBAC module."""

import pytest

from deerflow.enterprise.rbac import (
    RBACEngine,
    Role,
    check_permission,
    get_rbac_engine,
    initialize_default_policies,
    require_permission,
)


class TestRole:
    """Test Role enum."""

    def test_role_enum_values(self):
        assert Role.TENANT_ADMIN.value == "tenant_admin"
        assert Role.PROJECT_MANAGER.value == "project_manager"
        assert Role.DEVELOPER.value == "developer"
        assert Role.OPERATOR.value == "operator"
        assert Role.EXTERNAL.value == "external"


class TestRBACEngine:
    """Test RBACEngine core functionality."""

    def test_engine_initialization(self):
        engine = RBACEngine()
        assert engine.enforcer is not None

    def test_engine_with_default_model(self):
        engine = RBACEngine()
        # Default model should be loaded
        assert engine.enforcer.get_model() is not None

    def test_add_role_for_user(self):
        engine = RBACEngine()
        result = engine.add_role_for_user("user_123", "tenant_admin", "tenant_abc")
        assert result is True

        roles = engine.get_user_roles("user_123", "tenant_abc")
        assert "tenant_admin" in roles

    def test_remove_role_for_user(self):
        engine = RBACEngine()
        engine.add_role_for_user("user_123", "developer", "tenant_abc")
        assert "developer" in engine.get_user_roles("user_123", "tenant_abc")

        engine.remove_role_for_user("user_123", "developer", "tenant_abc")
        assert "developer" not in engine.get_user_roles("user_123", "tenant_abc")

    def test_add_and_check_permission(self):
        engine = RBACEngine()
        engine.add_role_for_user("user_123", "developer", "tenant_abc")
        engine.add_policy("developer", "tenant_abc", "agent", "read")

        assert engine.check_permission("user_123", "tenant_abc", "agent", "read")

    def test_check_permission_denied(self):
        engine = RBACEngine()
        engine.add_role_for_user("user_123", "operator", "tenant_abc")
        # No policy granted for delete

        assert not engine.check_permission("user_123", "tenant_abc", "agent", "delete")

    def test_remove_policy(self):
        engine = RBACEngine()
        engine.add_role_for_user("user_123", "developer", "tenant_abc")
        engine.add_policy("developer", "tenant_abc", "agent", "delete")
        assert engine.check_permission("user_123", "tenant_abc", "agent", "delete")

        engine.remove_policy("developer", "tenant_abc", "agent", "delete")
        assert not engine.check_permission("user_123", "tenant_abc", "agent", "delete")

    def test_check_permission_different_tenant(self):
        engine = RBACEngine()
        engine.add_role_for_user("user_123", "developer", "tenant_abc")
        engine.add_policy("developer", "tenant_abc", "agent", "read")

        # Should not have permission in different tenant
        assert not engine.check_permission("user_123", "tenant_xyz", "agent", "read")

    def test_get_user_roles_empty(self):
        engine = RBACEngine()
        roles = engine.get_user_roles("unknown_user", "tenant_abc")
        assert roles == []


class TestGlobalRBACEngine:
    """Test global RBAC engine instance."""

    def test_get_rbac_engine_returns_same_instance(self):
        engine1 = get_rbac_engine()
        engine2 = get_rbac_engine()
        assert engine1 is engine2


class TestPermissionHelpers:
    """Test permission helper functions."""

    def test_check_permission_global_engine(self):
        # Setup global engine
        engine = get_rbac_engine()
        engine.add_role_for_user("user_test", "developer", "tenant_test")
        engine.add_policy("developer", "tenant_test", "agent", "read")

        assert check_permission("user_test", "tenant_test", "agent", "read")
        assert not check_permission("user_test", "tenant_test", "agent", "delete")

    def test_require_permission_raises(self):
        with pytest.raises(PermissionError, match="does not have"):
            require_permission("user_test", "tenant_test", "agent", "admin")

    def test_require_permission_succeeds(self):
        engine = get_rbac_engine()
        engine.add_role_for_user("user_ok", "developer", "tenant_ok")
        engine.add_policy("developer", "tenant_ok", "agent", "read")

        # Should not raise
        require_permission("user_ok", "tenant_ok", "agent", "read")


class TestInitializeDefaultPolicies:
    """Test default policy initialization."""

    def test_initialize_default_policies(self):
        engine = RBACEngine()
        engine.add_role_for_user("admin_user", Role.TENANT_ADMIN, "default")
        initialize_default_policies(engine, tenant_id="default")

        # TENANT_ADMIN should have all permissions
        assert engine.check_permission("admin_user", "default", "agent", "admin")
