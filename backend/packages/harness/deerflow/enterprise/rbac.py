"""Role-Based Access Control (RBAC) implementation using Casbin.

This module provides permission checking for enterprise multi-tenant scenarios.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

import casbin

if TYPE_CHECKING:
    pass


class Role(StrEnum):
    """Standard RBAC roles for DeerFlow Enterprise.

    Hierarchy (high to low):
    - TENANT_ADMIN: Full tenant access
    - PROJECT_MANAGER: Project-level management
    - DEVELOPER: Create and modify agents
    - OPERATOR: Run agents and view results
    - EXTERNAL: Limited external access
    """

    TENANT_ADMIN = "tenant_admin"
    PROJECT_MANAGER = "project_manager"
    DEVELOPER = "developer"
    OPERATOR = "operator"
    EXTERNAL = "external"


# Default Casbin model configuration
DEFAULT_CASBIN_MODEL = """
[request_definition]
r = sub, dom, obj, act

[policy_definition]
p = sub, dom, obj, act

[role_definition]
g = _, _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub, r.dom) && r.dom == p.dom && r.obj == p.obj && r.act == p.act
"""


class RBACEngine:
    """Casbin-based RBAC engine for DeerFlow Enterprise.

    Supports multi-tenant policies using domain (tenant) separation.
    """

    def __init__(self, model_conf: str | None = None) -> None:
        """Initialize RBAC engine.

        Args:
            model_conf: Custom Casbin model configuration, or None for default
        """
        model_text = model_conf or DEFAULT_CASBIN_MODEL

        # Create model from text
        model = casbin.Model()
        model.load_model_from_text(model_text)

        # Create enforcer with model (no adapter for in-memory policies)
        self.enforcer = casbin.Enforcer(model)

    def add_role_for_user(
        self,
        user_id: str,
        role: Role | str,
        tenant_id: str,
    ) -> bool:
        """Assign a role to a user within a tenant."""
        return self.enforcer.add_grouping_policy(user_id, str(role), tenant_id)

    def remove_role_for_user(
        self,
        user_id: str,
        role: Role | str,
        tenant_id: str,
    ) -> bool:
        """Remove a role from a user within a tenant."""
        return self.enforcer.remove_grouping_policy(user_id, str(role), tenant_id)

    def add_policy(
        self,
        role: Role | str,
        tenant_id: str,
        resource: str,
        action: str,
    ) -> bool:
        """Add a permission policy for a role."""
        return self.enforcer.add_policy(str(role), tenant_id, resource, action)

    def remove_policy(
        self,
        role: Role | str,
        tenant_id: str,
        resource: str,
        action: str,
    ) -> bool:
        """Remove a permission policy."""
        return self.enforcer.remove_policy(str(role), tenant_id, resource, action)

    def check_permission(
        self,
        user_id: str,
        tenant_id: str,
        resource: str,
        action: str,
    ) -> bool:
        """Check if user has permission for resource/action in tenant."""
        return self.enforcer.enforce(user_id, tenant_id, resource, action)

    def get_user_roles(self, user_id: str, tenant_id: str) -> list[str]:
        """Get all roles assigned to a user in a tenant."""
        return self.enforcer.get_roles_for_user_in_domain(user_id, tenant_id)

    def load_policies_from_csv(self, csv_path: str) -> None:
        """Load policies from CSV file."""
        # For production, use database adapter
        pass


# Global engine instance (initialized on first use)
_global_engine: RBACEngine | None = None


def get_rbac_engine() -> RBACEngine:
    """Get or create global RBAC engine."""
    global _global_engine
    if _global_engine is None:
        _global_engine = RBACEngine()
    return _global_engine


def check_permission(
    user_id: str,
    tenant_id: str,
    resource: str,
    action: str,
) -> bool:
    """Check if user has permission (uses global engine)."""
    engine = get_rbac_engine()
    return engine.check_permission(user_id, tenant_id, resource, action)


def require_permission(
    user_id: str,
    tenant_id: str,
    resource: str,
    action: str,
) -> None:
    """Check permission and raise PermissionError if denied."""
    if not check_permission(user_id, tenant_id, resource, action):
        raise PermissionError(f"User {user_id} does not have {action} permission on {resource} in tenant {tenant_id}")


def initialize_default_policies(engine: RBACEngine | None = None, tenant_id: str = "default") -> None:
    """Initialize default role policies.

    This should be called during application startup.
    """
    e = engine or get_rbac_engine()

    # TENANT_ADMIN: Full access
    for action in ["create", "read", "update", "delete", "execute", "admin"]:
        for resource in ["agent", "thread", "sandbox", "skill", "memory", "audit_log"]:
            e.add_policy(Role.TENANT_ADMIN, tenant_id, resource, action)

    # PROJECT_MANAGER: Project management
    e.add_policy(Role.PROJECT_MANAGER, tenant_id, "agent", "create")
    e.add_policy(Role.PROJECT_MANAGER, tenant_id, "agent", "read")
    e.add_policy(Role.PROJECT_MANAGER, tenant_id, "agent", "update")
    e.add_policy(Role.PROJECT_MANAGER, tenant_id, "thread", "read")
    e.add_policy(Role.PROJECT_MANAGER, tenant_id, "sandbox", "read")

    # DEVELOPER: Agent development
    e.add_policy(Role.DEVELOPER, tenant_id, "agent", "create")
    e.add_policy(Role.DEVELOPER, tenant_id, "agent", "read")
    e.add_policy(Role.DEVELOPER, tenant_id, "agent", "update")
    e.add_policy(Role.DEVELOPER, tenant_id, "thread", "read")
    e.add_policy(Role.DEVELOPER, tenant_id, "thread", "execute")

    # OPERATOR: Run and monitor
    e.add_policy(Role.OPERATOR, tenant_id, "agent", "read")
    e.add_policy(Role.OPERATOR, tenant_id, "agent", "execute")
    e.add_policy(Role.OPERATOR, tenant_id, "thread", "read")
    e.add_policy(Role.OPERATOR, tenant_id, "sandbox", "read")

    # EXTERNAL: Minimal access
    e.add_policy(Role.EXTERNAL, tenant_id, "agent", "read")
    e.add_policy(Role.EXTERNAL, tenant_id, "thread", "read")
