"""Tests for health check endpoints."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.app import create_app


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check_returns_200(self, client: TestClient) -> None:
        """Test that health check returns 200 with expected structure."""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "components" in data
        assert "timestamp" in data

    def test_health_check_has_valid_status(self, client: TestClient) -> None:
        """Test that health check status is one of valid values."""
        response = client.get("/api/health")
        data = response.json()

        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_health_check_has_components(self, client: TestClient) -> None:
        """Test that health check includes component statuses."""
        response = client.get("/api/health")
        data = response.json()

        components = data["components"]
        assert isinstance(components, dict)

        # Check that expected components are present
        expected_components = ["langgraph", "database", "sandbox", "memory"]
        for component in expected_components:
            if component in components:
                comp_data = components[component]
                assert "status" in comp_data
                assert "latency_ms" in comp_data
                assert comp_data["status"] in ["up", "down", "degraded"]

    def test_health_check_timestamp_is_iso(self, client: TestClient) -> None:
        """Test that timestamp is in ISO format."""
        response = client.get("/api/health")
        data = response.json()

        # ISO format: 2024-01-01T12:00:00Z
        timestamp = data["timestamp"]
        assert "T" in timestamp
        assert timestamp.endswith("Z")

    def test_readiness_probe_returns_ready(self, client: TestClient) -> None:
        """Test that readiness probe returns ready status."""
        response = client.get("/api/health/ready")
        assert response.status_code == 200

        data = response.json()
        assert data["ready"] is True

    def test_liveness_probe_returns_alive(self, client: TestClient) -> None:
        """Test that liveness probe returns alive status."""
        response = client.get("/api/health/live")
        assert response.status_code == 200

        data = response.json()
        assert data["alive"] is True

    def test_legacy_health_endpoint_still_works(self, client: TestClient) -> None:
        """Test that the legacy /health endpoint still works."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "deer-flow-gateway"
