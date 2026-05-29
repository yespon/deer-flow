from dataclasses import dataclass
import random


@dataclass
class SyntheticTenant:
    id: str
    name: str
    plan: str
    quota_config: dict


class SyntheticTenantGenerator:
    """Generate synthetic tenants for testing."""

    PLANS = ["free", "pro", "enterprise"]

    def generate(self, count: int) -> list[SyntheticTenant]:
        tenants = []
        for i in range(count):
            plan = random.choice(self.PLANS)
            tenants.append(SyntheticTenant(
                id=f"tenant_{i:04d}",
                name=f"Company {i}",
                plan=plan,
                quota_config=self._quota_for_plan(plan),
            ))
        return tenants

    def _quota_for_plan(self, plan: str) -> dict:
        quotas = {
            "free": {"max_sandboxes": 2, "max_api_calls": 100},
            "pro": {"max_sandboxes": 5, "max_api_calls": 1000},
            "enterprise": {"max_sandboxes": 20, "max_api_calls": 10000},
        }
        return quotas.get(plan, quotas["free"])
