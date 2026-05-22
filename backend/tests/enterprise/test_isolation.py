"""Tests for DeerFlow Enterprise data isolation."""

import pytest

from deerflow.enterprise.isolation import (
    TenantNamespace,
    get_tenant_prefix,
    namespaced_collection,
    namespaced_key,
    namespaced_path,
    namespaced_table,
)
from deerflow.enterprise.tenancy import Tenant


class TestTenantNamespace:
    """Test TenantNamespace class."""

    def test_namespace_creation_from_tenant(self):
        tenant = Tenant(id="tenant_123", name="Test")
        ns = TenantNamespace(tenant)

        assert ns.tenant_id == "tenant_123"
        assert ns.prefix == "tenant_123"

    def test_namespace_creation_from_string(self):
        ns = TenantNamespace("tenant_abc")

        assert ns.tenant_id == "tenant_abc"
        assert ns.prefix == "tenant_abc"

    def test_apply_to_table_name(self):
        tenant = Tenant(id="tenant_abc", name="Test")
        ns = TenantNamespace(tenant)

        result = ns.apply_to_table("threads")
        assert result == "tenant_abc_threads"

    def test_apply_to_path(self):
        tenant = Tenant(id="tenant_xyz", name="Test")
        ns = TenantNamespace(tenant)

        result = ns.apply_to_path("/data", "uploads")
        assert result == "/data/tenant_xyz/uploads"

    def test_apply_to_path_no_segments(self):
        tenant = Tenant(id="tenant_xyz", name="Test")
        ns = TenantNamespace(tenant)

        result = ns.apply_to_path("/data")
        assert result == "/data/tenant_xyz"

    def test_apply_to_collection_name(self):
        tenant = Tenant(id="tenant_vec", name="Test")
        ns = TenantNamespace(tenant)

        result = ns.apply_to_collection("memories")
        assert result == "tenant_vec_memories"

    def test_apply_to_key(self):
        tenant = Tenant(id="tenant_key", name="Test")
        ns = TenantNamespace(tenant)

        result = ns.apply_to_key("session:abc123")
        assert result == "tenant_key:session:abc123"


class TestNamespaceHelpers:
    """Test namespace helper functions."""

    def test_get_tenant_prefix_with_tenant(self):
        tenant = Tenant(id="tenant_123", name="Test")
        assert get_tenant_prefix(tenant) == "tenant_123"

    def test_get_tenant_prefix_with_string(self):
        assert get_tenant_prefix("tenant_456") == "tenant_456"

    def test_namespaced_table(self):
        result = namespaced_table("tenant_789", "agents")
        assert result == "tenant_789_agents"

    def test_namespaced_path(self):
        result = namespaced_path("tenant_aaa", "/workspace")
        assert result == "/workspace/tenant_aaa"

    def test_namespaced_path_with_segments(self):
        result = namespaced_path("tenant_aaa", "/workspace", "uploads", "files")
        assert result == "/workspace/tenant_aaa/uploads/files"

    def test_namespaced_collection(self):
        result = namespaced_collection("tenant_bbb", "vectors")
        assert result == "tenant_bbb_vectors"

    def test_namespaced_key(self):
        result = namespaced_key("tenant_ccc", "cache:data")
        assert result == "tenant_ccc:cache:data"
