"""Locust load test scenarios for DeerFlow Enterprise.

Run with: locust -f locustfile.py --host http://localhost:8001
"""

from locust import HttpUser, task, between


class EnterpriseUser(HttpUser):
    """Simulate enterprise user load."""

    wait_time = between(1, 5)

    def on_start(self):
        """Setup user session."""
        self.tenant_id = "load_test_tenant"
        self.user_id = f"user_{self.user_id}"

    @task(10)
    def health_check(self):
        """Basic health check endpoint."""
        self.client.get("/health")

    @task(5)
    def agent_chat(self):
        """Chat with agent endpoint."""
        # Note: This is a placeholder - actual endpoint may differ
        self.client.post(
            "/api/threads",
            json={"tenant_id": self.tenant_id},
            headers={"X-Tenant-ID": self.tenant_id},
            name="/api/threads",
        )

    @task(3)
    def knowledge_search(self):
        """Search knowledge base."""
        self.client.post(
            "/api/kb/search",
            json={
                "query": "refund policy",
                "tenant_id": self.tenant_id,
            },
            headers={"X-Tenant-ID": self.tenant_id},
            name="/api/kb/search",
        )

    @task(1)
    def check_quota(self):
        """Check quota endpoint."""
        self.client.get(
            "/api/quota/status",
            headers={"X-Tenant-ID": self.tenant_id},
            name="/api/quota/status",
        )


class AdminUser(HttpUser):
    """Simulate admin user with more operations."""

    wait_time = between(2, 10)

    def on_start(self):
        """Setup admin session."""
        self.tenant_id = "admin_tenant"

    @task(5)
    def list_tenants(self):
        """List tenants (admin only)."""
        self.client.get(
            "/api/admin/tenants",
            headers={"X-Tenant-ID": self.tenant_id},
            name="/api/admin/tenants",
        )

    @task(2)
    def view_audit_logs(self):
        """View audit logs."""
        self.client.get(
            "/api/admin/audit-logs",
            headers={"X-Tenant-ID": self.tenant_id},
            name="/api/admin/audit-logs",
        )
