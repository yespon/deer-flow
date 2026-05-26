"""Tests for QuotaManager with Redis counters."""

import pytest
from unittest.mock import Mock

from deerflow.enterprise.quota import QuotaExceededError, QuotaManager


class TestQuotaManager:
    @pytest.fixture
    def mock_redis(self):
        return Mock()

    @pytest.fixture
    def quota_manager(self, mock_redis):
        return QuotaManager(mock_redis)

    def test_acquire_succeeds_when_under_limit(self, quota_manager, mock_redis):
        mock_redis.incr.return_value = 3

        result = quota_manager.acquire("tenant_123", "concurrent_sandboxes", limit=5)

        assert result is True
        mock_redis.incr.assert_called_once_with("quota:tenant_123:concurrent_sandboxes")

    def test_acquire_fails_when_at_limit(self, quota_manager, mock_redis):
        mock_redis.incr.return_value = 6

        result = quota_manager.acquire("tenant_123", "concurrent_sandboxes", limit=5)

        assert result is False
        mock_redis.decr.assert_called_once_with("quota:tenant_123:concurrent_sandboxes")

    def test_release_decrements_counter(self, quota_manager, mock_redis):
        mock_redis.decr.return_value = 0

        quota_manager.release("tenant_123", "concurrent_sandboxes")

        mock_redis.decr.assert_called_once_with("quota:tenant_123:concurrent_sandboxes")

    def test_get_usage_returns_current_value(self, quota_manager, mock_redis):
        mock_redis.get.return_value = "3"

        usage = quota_manager.get_usage("tenant_123", "concurrent_sandboxes")

        assert usage == 3

    def test_get_usage_returns_zero_when_none(self, quota_manager, mock_redis):
        mock_redis.get.return_value = None

        usage = quota_manager.get_usage("tenant_123", "concurrent_sandboxes")

        assert usage == 0

    def test_check_quota_raises_when_exceeded(self, quota_manager, mock_redis):
        mock_redis.get.return_value = "6"

        with pytest.raises(QuotaExceededError) as exc_info:
            quota_manager.check_quota("tenant_123", "concurrent_sandboxes", limit=5)

        assert "concurrent_sandboxes" in str(exc_info.value)
        assert "5" in str(exc_info.value)

    def test_check_quota_passes_when_under_limit(self, quota_manager, mock_redis):
        mock_redis.get.return_value = "3"

        # Should not raise
        quota_manager.check_quota("tenant_123", "concurrent_sandboxes", limit=5)

    def test_acquire_with_ttl(self, quota_manager, mock_redis):
        mock_redis.incr.return_value = 1

        quota_manager.acquire("tenant_123", "daily_api_calls", limit=1000, ttl_seconds=86400)

        mock_redis.expire.assert_called_once_with("quota:tenant_123:daily_api_calls", 86400)

    def test_multiple_resources_independent(self, quota_manager, mock_redis):
        mock_redis.get.side_effect = ["2", "50"]

        sandbox_usage = quota_manager.get_usage("tenant_123", "concurrent_sandboxes")
        api_usage = quota_manager.get_usage("tenant_123", "daily_api_calls")

        assert sandbox_usage == 2
        assert api_usage == 50

    def test_release_does_not_go_negative(self, quota_manager, mock_redis):
        mock_redis.decr.return_value = -1
        mock_redis.get.return_value = "-1"

        quota_manager.release("tenant_123", "concurrent_sandboxes")

        mock_redis.set.assert_called_once_with("quota:tenant_123:concurrent_sandboxes", 0)
