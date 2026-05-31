"""Tests for QuotaConfig and TenantQuota models."""

import pytest
from pydantic import ValidationError

from deerflow.enterprise.quota_config import QuotaConfig, TenantQuota


class TestTenantQuota:
    """Test cases for TenantQuota model."""

    def test_default_quota_values(self):
        """Test that TenantQuota has sensible defaults."""
        quota = TenantQuota()
        assert quota.max_concurrent_sandboxes >= 0
        assert quota.max_cpu_cores >= 0
        assert quota.max_memory_gb >= 0
        assert quota.max_storage_gb >= 0
        assert quota.max_network_egress_mb >= 0

    def test_custom_quota_values(self):
        """Test that TenantQuota accepts custom values."""
        quota = TenantQuota(
            max_concurrent_sandboxes=10,
            max_cpu_cores=4,
            max_memory_gb=16,
            max_storage_gb=100,
            max_network_egress_mb=1000,
        )
        assert quota.max_concurrent_sandboxes == 10
        assert quota.max_cpu_cores == 4
        assert quota.max_memory_gb == 16
        assert quota.max_storage_gb == 100
        assert quota.max_network_egress_mb == 1000

    def test_negative_quota_rejected(self):
        """Test that negative quota values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TenantQuota(max_concurrent_sandboxes=-1)
        assert "max_concurrent_sandboxes" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            TenantQuota(max_cpu_cores=-1)
        assert "max_cpu_cores" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            TenantQuota(max_memory_gb=-1)
        assert "max_memory_gb" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            TenantQuota(max_storage_gb=-1)
        assert "max_storage_gb" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            TenantQuota(max_network_egress_mb=-1)
        assert "max_network_egress_mb" in str(exc_info.value)


class TestQuotaConfig:
    """Test cases for QuotaConfig model."""

    def test_default_config(self):
        """Test that QuotaConfig has sensible defaults."""
        config = QuotaConfig()
        assert config.enabled is False
        assert config.enforcement_mode in ["hard", "soft"]
        assert config.default_quotas is not None
        assert isinstance(config.default_quotas, TenantQuota)

    def test_enabled_config(self):
        """Test that QuotaConfig can be enabled."""
        config = QuotaConfig(enabled=True)
        assert config.enabled is True

        config = QuotaConfig(enabled=False)
        assert config.enabled is False

    def test_custom_redis_url(self):
        """Test that QuotaConfig accepts valid Redis URLs."""
        # Test redis:// URL (without /0 suffix as per spec)
        config = QuotaConfig(redis_url="redis://localhost:6379")
        assert config.redis_url == "redis://localhost:6379"

        # Test rediss:// URL (secure)
        config = QuotaConfig(redis_url="rediss://localhost:6379")
        assert config.redis_url == "rediss://localhost:6379"

        # Test unix:// URL
        config = QuotaConfig(redis_url="unix:///var/run/redis/redis.sock")
        assert config.redis_url == "unix:///var/run/redis/redis.sock"

    def test_invalid_redis_url_rejected(self):
        """Test that invalid Redis URLs are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            QuotaConfig(redis_url="http://localhost:6379")
        assert "redis_url" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            QuotaConfig(redis_url="invalid_url")
        assert "redis_url" in str(exc_info.value)

    def test_enforcement_mode_values(self):
        """Test that enforcement_mode only accepts 'hard' or 'soft'."""
        config_hard = QuotaConfig(enforcement_mode="hard")
        assert config_hard.enforcement_mode == "hard"

        config_soft = QuotaConfig(enforcement_mode="soft")
        assert config_soft.enforcement_mode == "soft"

        # Invalid value should raise validation error
        with pytest.raises(ValidationError):
            QuotaConfig(enforcement_mode="invalid")
