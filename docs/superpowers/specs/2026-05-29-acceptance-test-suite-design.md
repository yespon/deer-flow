# DeerFlow Enterprise Acceptance Test Suite Design

**Date:** 2026-05-29  
**Status:** Approved  
**Author:** Claude Code  

---

## Overview

This document describes the comprehensive acceptance test suite for DeerFlow Enterprise, covering all validation requirements from the enterprise architecture specification.

## Goals

1. Validate system meets enterprise-grade requirements
2. Ensure production readiness before deployment
3. Provide automated regression detection
4. Establish performance baselines

---

## Architecture

### Test Suite Structure

```
┌─────────────────────────────────────────────────────────┐
│              全量验收测试套件 (Acceptance Test Suite)        │
├─────────────────────────────────────────────────────────┤
│  CI 集成测试 (每次提交)                                    │
│  ├── 安全审计验证 (test_security_audit.py)                │
│  ├── 权限边界测试 (test_permission_boundaries.py)         │
│  └── 租户隔离测试 (test_tenant_isolation.py)              │
├─────────────────────────────────────────────────────────┤
│  独立验收测试 (按需/定时)                                   │
│  ├── 压力测试 (test_load_stress.py)                       │
│  │   ├── 企业功能层：多租户上下文、配额、审批               │
│  │   └── 存储层：PostgreSQL、Redis、向量数据库              │
│  └── RAG 准确率评测 (test_rag_accuracy.py)                │
│      └── 使用真实行业文档评估检索质量                      │
├─────────────────────────────────────────────────────────┤
│  执行环境                                                  │
│  ├── 本地 Docker：开发迭代验证                              │
│  └── 云环境：生产级最终验收                                 │
└─────────────────────────────────────────────────────────┘
```

### Execution Strategy: Hybrid Mode

| Test Category | Trigger | Environment |
|--------------|---------|-------------|
| CI Integration Tests | Every commit | CI runner |
| Load Stress Tests | On-demand / Nightly | Local Docker / Cloud |
| RAG Accuracy Tests | Release candidate | Cloud with GPU |

---

## Test Data Strategy

### Hybrid Data Approach

| Test Type | Data Source | Scale |
|-----------|-------------|-------|
| **Stress Tests** | Synthetic data generator | 100+ tenants, 100K+ documents |
| **RAG Evaluation** | Real industry documents (anonymized) | 1,000+ Q&A pairs |
| **Security Audit** | Synthetic tenants + real attack scenarios | 50+ security cases |

### Data Generation

```python
# Synthetic tenant generator
class SyntheticTenantGenerator:
    def generate(self, count: int) -> list[Tenant]:
        """Generate N synthetic tenants with realistic configs."""

# Document corpus generator
class DocumentCorpusGenerator:
    def generate(self, tenant_id: str, count: int) -> list[KnowledgeDocument]:
        """Generate documents with varied content types."""

# Q&A pair generator for RAG evaluation
class QAGenerator:
    def generate(self, documents: list[KnowledgeDocument]) -> list[QAPair]:
        """Generate question-answer pairs from documents."""
```

---

## Test Categories

### 1. CI Integration Tests

Run on every commit to ensure basic enterprise functionality.

#### 1.1 Security Audit Tests

**File:** `tests/enterprise/test_security_audit.py`

| Test Case | Description |
|-----------|-------------|
| `test_permission_boundaries` | Verify RBAC prevents unauthorized access |
| `test_tenant_isolation` | Ensure no cross-tenant data leakage |
| `test_audit_log_integrity` | Validate audit chain signatures |
| `test_sensitive_data_detection` | Verify PII detection and blocking |

**Success Criteria:**
- 100% of permission checks return correct results
- No cross-tenant data access possible
- All audit events cryptographically verifiable

#### 1.2 Permission Boundary Tests

**File:** `tests/enterprise/test_permission_boundaries.py`

```python
class TestPermissionBoundaries:
    async def test_admin_has_all_permissions(self):
        """Tenant admin should have complete access within tenant."""

    async def test_external_user_restricted(self):
        """External users should have limited read-only access."""

    async def test_cross_tenant_denied(self):
        """Users cannot access resources outside their tenant."""
```

#### 1.3 Tenant Isolation Tests

**File:** `tests/enterprise/test_tenant_isolation.py`

```python
class TestTenantIsolation:
    async def test_namespace_separation(self):
        """Each tenant has unique namespace for all resources."""

    async def test_knowledge_base_isolation(self):
        """KB queries only return tenant's own documents."""

    async def test_sandbox_isolation(self):
        """Sandbox operations isolated per tenant."""
```

### 2. Load Stress Tests

**File:** `tests/enterprise/test_load_stress.py`

#### 2.1 Enterprise Function Layer

Test multi-tenant context switching and enterprise features under load.

| Scenario | Concurrent | Duration | Metric |
|----------|-----------|----------|--------|
| Tenant context switch | 100 | 60s | < 5ms per switch |
| Quota check | 1000 | 60s | < 10ms per check |
| Approval workflow | 50 | 60s | < 100ms per step |
| Agent team orchestration | 20 teams | 60s | < 2s per task |

**Test Implementation:**

```python
class TestEnterpriseFunctionLoad:
    async def test_tenant_context_switching(self):
        """Rapid tenant context switches."""
        # 100 concurrent tenants
        # Each performs 100 operations
        # Measure latency and consistency

    async def test_quota_enforcement_under_load(self):
        """Quota checks during high concurrency."""
        # 1000 concurrent requests
        # Verify 100% enforcement accuracy

    async def test_approval_workflow_throughput(self):
        """Approval request processing rate."""
        # 50 concurrent approval workflows
        # Measure end-to-end latency
```

#### 2.2 Storage Layer Tests

Test database and cache performance under load.

| Component | Operation | Concurrency | Target |
|-----------|-----------|-------------|--------|
| PostgreSQL | Read/Write | 500 | < 50ms |
| Redis | Quota counter | 1000 | < 5ms |
| Chroma | Vector search | 100 | < 100ms |

**Test Implementation:**

```python
class TestStorageLayerLoad:
    async def test_postgresql_tenant_queries(self):
        """PostgreSQL concurrent tenant queries."""

    async def test_redis_quota_counters(self):
        """Redis distributed counter performance."""

    async def test_chroma_vector_search(self):
        """Vector store concurrent search performance."""
```

### 3. RAG Accuracy Evaluation

**File:** `tests/enterprise/test_rag_accuracy.py`

#### Evaluation Methodology

```python
class RAGAccuracyEvaluator:
    """Evaluate RAG system accuracy using standard metrics."""

    def evaluate(self, qa_pairs: list[QAPair]) -> EvaluationResult:
        """
        Metrics:
        - Hit Rate @ K: Is correct doc in top K?
        - MRR: Mean Reciprocal Rank
        - NDCG: Normalized Discounted Cumulative Gain
        """
```

#### Test Dataset

| Category | Documents | Questions | Source |
|----------|-----------|-----------|--------|
| HR Policies | 50 | 200 | Synthetic HR docs |
| IT Support | 100 | 400 | Real tickets (anonymized) |
| Product Manuals | 200 | 600 | Public documentation |

**Success Criteria:**
- Top-5 Hit Rate ≥ 85%
- MRR ≥ 0.75
- NDCG @ 10 ≥ 0.80

---

## Execution Environments

### Local Docker (Development)

**File:** `docker-compose.test.yml`

```yaml
services:
  test-runner:
    build: .
    environment:
      - TEST_MODE=acceptance
      - TENANT_COUNT=10  # Scaled down for local
    depends_on:
      - postgres
      - redis
      - chroma
```

**Usage:**
```bash
make test-acceptance-local
```

### Cloud Environment (Final Validation)

**Infrastructure:**
- Kubernetes cluster with autoscaling
- Dedicated load generators
- Monitoring stack (Prometheus + Grafana)

**Usage:**
```bash
make test-acceptance-cloud
```

---

## Acceptance Criteria Mapping

| Spec Requirement | Test Implementation | Pass Criteria |
|-----------------|---------------------|---------------|
| 压力测试：100+租户并发 | `test_load_stress.py` | Response time < 2s, Error rate < 1% |
| RAG准确率 > 85% | `test_rag_accuracy.py` | Top-5 accuracy ≥ 85% |
| 审计日志不可篡改 | `test_audit_integrity.py` | Signature verification 100% |
| 合规检出率 > 95% | `test_compliance_detection.py` | Detection ≥ 95%, FP < 5% |
| 租户切换开销 < 5ms | `test_tenant_context.py` | Mean < 5ms, P99 < 10ms |

---

## Implementation Plan

### Phase 1: Core Infrastructure
1. Synthetic data generators
2. Test harness and fixtures
3. CI integration setup

### Phase 2: CI Tests
1. Security audit tests
2. Permission boundary tests
3. Tenant isolation tests

### Phase 3: Load Tests
1. Enterprise function layer tests
2. Storage layer tests
3. Docker Compose setup

### Phase 4: RAG Evaluation
1. Test dataset curation
2. Evaluation framework
3. Cloud environment setup

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test Coverage | > 90% | Line coverage report |
| CI Test Duration | < 5 min | CI pipeline time |
| Load Test Duration | < 30 min | Nightly run time |
| RAG Evaluation | < 60 min | Full dataset evaluation |

---

## Appendix

### A. Test Data Format

```json
{
  "tenant": {
    "id": "tenant_001",
    "name": "Acme Corp",
    "plan": "enterprise",
    "quota": {
      "max_concurrent_sandboxes": 10,
      "max_api_calls_per_hour": 10000
    }
  },
  "qa_pair": {
    "question": "What is the refund policy?",
    "expected_answer": "Full refund within 30 days",
    "relevant_doc_ids": ["doc_001", "doc_003"]
  }
}
```

### B. References

- [DeerFlow Enterprise Architecture Spec](2026-05-22-enterprise-architecture-spec.md)
- [ENTERPRISE_API.md](../../../ENTERPRISE_API.md)
- [ENTERPRISE_DEPLOYMENT.md](../../../ENTERPRISE_DEPLOYMENT.md)
