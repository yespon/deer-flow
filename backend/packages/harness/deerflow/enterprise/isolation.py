"""Data isolation utilities for multi-tenancy.

Provides namespace management for tables, files, and collections.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deerflow.enterprise.tenancy import Tenant


class TenantNamespace:
    """Manages resource namespacing for a tenant.

    This class provides methods to generate tenant-scoped names for:
    - Database tables (strict mode): tenant_{id}_{table}
    - File paths: /base/tenant_{id}/...
    - Vector collections: tenant_{id}_{collection}
    """

    def __init__(self, tenant: Tenant | str) -> None:
        if isinstance(tenant, str):
            self._tenant_id = tenant
        else:
            self._tenant_id = tenant.id

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    @property
    def prefix(self) -> str:
        """Return the namespace prefix for this tenant."""
        return self._tenant_id

    def apply_to_table(self, table_name: str) -> str:
        """Generate tenant-scoped table name.

        Example: tenant_123_threads
        """
        return f"{self._tenant_id}_{table_name}"

    def apply_to_path(self, base_path: str, *segments: str) -> str:
        """Generate tenant-scoped file path.

        Example: /data/tenant_123/uploads
        """
        # Insert tenant prefix after base path
        path = os.path.join(base_path, self._tenant_id, *segments)
        return path

    def apply_to_collection(self, collection_name: str) -> str:
        """Generate tenant-scoped collection name for vector stores.

        Example: tenant_123_memories
        """
        return f"{self._tenant_id}_{collection_name}"

    def apply_to_key(self, key: str) -> str:
        """Generate tenant-scoped key for caches and stores.

        Example: tenant_123:session:abc123
        """
        return f"{self._tenant_id}:{key}"


def get_tenant_prefix(tenant: Tenant | str) -> str:
    """Get namespace prefix from tenant or tenant_id."""
    if isinstance(tenant, str):
        return tenant
    return tenant.id


def namespaced_table(tenant_id: str, table_name: str) -> str:
    """Generate tenant-scoped table name."""
    return f"{tenant_id}_{table_name}"


def namespaced_path(tenant_id: str, base_path: str, *segments: str) -> str:
    """Generate tenant-scoped file path."""
    return os.path.join(base_path, tenant_id, *segments)


def namespaced_collection(tenant_id: str, collection_name: str) -> str:
    """Generate tenant-scoped collection name."""
    return f"{tenant_id}_{collection_name}"


def namespaced_key(tenant_id: str, key: str) -> str:
    """Generate tenant-scoped key."""
    return f"{tenant_id}:{key}"
