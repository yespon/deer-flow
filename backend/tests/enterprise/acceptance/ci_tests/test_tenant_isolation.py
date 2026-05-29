"""CI Integration tests for tenant isolation validation.

Fast-running tests for CI pipeline verifying tenant data isolation.
"""

from deerflow.enterprise import Tenant, TenantNamespace


class TestTenantIsolation:
    """Test tenant data isolation."""

    def test_namespace_separation(self):
        """Each tenant has unique namespace for all resources."""
        tenant_a = Tenant(id="tenant_a", name="Tenant A")
        tenant_b = Tenant(id="tenant_b", name="Tenant B")

        ns_a = TenantNamespace(tenant_a.id)
        ns_b = TenantNamespace(tenant_b.id)

        # All resource types should be namespaced
        col_a = ns_a.apply_to_collection("knowledge")
        col_b = ns_b.apply_to_collection("knowledge")

        assert col_a != col_b
        assert tenant_a.id in col_a
        assert tenant_b.id in col_b

    def test_table_name_isolation(self):
        """Database tables are namespaced per tenant."""
        tenant_a = Tenant(id="tenant_a", name="Tenant A")
        ns_a = TenantNamespace(tenant_a.id)

        table_a = ns_a.apply_to_table("users")

        assert table_a == "tenant_a_users"
        assert "tenant_b" not in table_a

    def test_key_isolation(self):
        """Cache/storage keys are namespaced per tenant."""
        tenant_a = Tenant(id="tenant_a", name="Tenant A")
        ns_a = TenantNamespace(tenant_a.id)

        key_a = ns_a.apply_to_key("session:abc123")

        assert key_a.startswith("tenant_a:")
        assert "tenant_b" not in key_a

    def test_path_isolation(self):
        """File system paths are namespaced per tenant."""
        tenant_a = Tenant(id="tenant_a", name="Tenant A")
        ns_a = TenantNamespace(tenant_a.id)

        path_a = ns_a.apply_to_path("/data", "uploads")

        assert "tenant_a" in path_a
        assert "tenant_b" not in path_a

    def test_no_cross_tenant_access(self):
        """Collections not accessible across tenants."""
        tenant_a = Tenant(id="tenant_a", name="Tenant A")
        ns_a = TenantNamespace(tenant_a.id)

        collection_a = ns_a.apply_to_collection("knowledge")

        assert "tenant_b" not in collection_a
