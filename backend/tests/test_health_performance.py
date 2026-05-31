"""
Performance tests for health check endpoints.

Verifies that health checks respond within acceptable time limits
even under load.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
import requests


class TestHealthCheckPerformance:
    """Performance tests for health check endpoints."""

    @pytest.fixture
    def base_url(self) -> str:
        """Get the base URL for the backend."""
        return "http://localhost:8001"

    def test_health_response_time(self, base_url: str):
        """Verify health endpoint responds within 500ms."""
        start = time.time()
        response = requests.get(f"{base_url}/api/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 0.5, f"Health check took {elapsed:.3f}s, expected < 0.5s"

    def test_readiness_response_time(self, base_url: str):
        """Verify readiness probe responds within 100ms."""
        start = time.time()
        response = requests.get(f"{base_url}/api/health/ready")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 0.1, f"Readiness probe took {elapsed:.3f}s, expected < 0.1s"

    def test_liveness_response_time(self, base_url: str):
        """Verify liveness probe responds within 100ms."""
        start = time.time()
        response = requests.get(f"{base_url}/api/health/live")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 0.1, f"Liveness probe took {elapsed:.3f}s, expected < 0.1s"

    def test_health_concurrent_requests(self, base_url: str):
        """Verify health endpoint handles concurrent requests."""
        num_requests = 50
        max_time = 2.0  # seconds

        def make_request():
            start = time.time()
            try:
                response = requests.get(f"{base_url}/api/health", timeout=5)
                return response.status_code == 200, time.time() - start
            except Exception:
                return False, time.time() - start

        start = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            results = [future.result() for future in as_completed(futures)]

        total_time = time.time() - start

        success_count = sum(1 for success, _ in results if success)
        assert success_count == num_requests, f"Only {success_count}/{num_requests} requests succeeded"
        assert total_time < max_time, f"Concurrent requests took {total_time:.3f}s, expected < {max_time}s"

    def test_health_under_load(self, base_url: str):
        """Test health endpoint under sustained load."""
        num_iterations = 100
        errors = []
        response_times = []

        for _ in range(num_iterations):
            start = time.time()
            try:
                response = requests.get(f"{base_url}/api/health", timeout=2)
                if response.status_code != 200:
                    errors.append(f"Status {response.status_code}")
                response_times.append(time.time() - start)
            except Exception as e:
                errors.append(str(e))

        # Should have no errors
        assert len(errors) == 0, f"Errors during load test: {errors}"

        # 95th percentile should be under 200ms
        response_times.sort()
        p95 = response_times[int(len(response_times) * 0.95)]
        assert p95 < 0.2, f"P95 response time {p95:.3f}s exceeds 200ms"


class TestResilientStreamPerformance:
    """Performance tests for resilient streaming."""

    @pytest.fixture
    def base_url(self) -> str:
        """Get the base URL for the backend."""
        return "http://localhost:8001"

    def test_connection_pool_reuse(self, base_url: str):
        """Verify HTTP connection pooling is working."""
        session = requests.Session()

        # Make multiple requests
        times = []
        for _ in range(10):
            start = time.time()
            response = session.get(f"{base_url}/api/health")
            times.append(time.time() - start)
            assert response.status_code == 200

        # First request may be slower (connection setup)
        # Subsequent requests should be faster
        avg_later = sum(times[2:]) / len(times[2:])
        assert avg_later < 0.05, f"Average response time {avg_later:.3f}s too slow"

        session.close()
