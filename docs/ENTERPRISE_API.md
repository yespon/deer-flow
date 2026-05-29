# DeerFlow Enterprise API Reference

## Overview

DeerFlow Enterprise extends the base DeerFlow platform with multi-tenancy, RBAC, audit logging, approval workflows, agent teams, knowledge base RAG, brand compliance, and content filtering capabilities.

All enterprise modules live under `deerflow.enterprise` and are configured via `config.yaml`.

---

## Module Index

| Module | Description |
|--------|-------------|
| `tenancy` | Multi-tenant context and isolation |
| `isolation` | Tenant namespace management |
| `rbac` | Role-based access control |
| `audit` | Immutable audit logging |
| `quota` | Resource quota management |
| `approval` | Human-in-Loop approval workflows |
| `agent_registry` | Agent type registration |
| `task_decomposer` | LLM-driven task decomposition |
| `agent_team_orchestrator` | Multi-agent parallel execution |
| `knowledge_base` | Corporate knowledge base with RAG |
| `brand_controller` | Brand compliance checking |
| `compliance_filter` | Content compliance filtering |
| `enterprise_sandbox` | Audited sandbox provider |
| `performance` | Caching and batching optimizations |

---

## Multi-Tenancy

### Tenant Context

```python
from deerflow.enterprise import get_current_tenant, set_current_tenant, tenant_context

# Set current tenant
tenant = Tenant(id="tenant_abc", name="Acme Corp", plan="enterprise")
set_current_tenant(tenant)

# Get current tenant
current = get_current_tenant()
assert current.id == "tenant_abc"

# Use context manager
async with tenant_context("tenant_abc"):
    # All operations within this scope use tenant_abc
    result = await agent.run(task)
```

### Tenant Isolation

```python
from deerflow.enterprise import TenantNamespace

ns = TenantNamespace("tenant_abc")

# Apply namespace to different resource types
table = ns.apply_to_table("users")         # tenant_tenant_abc_users
path = ns.apply_to_path("/data/files")      # /tenant_tenant_abc/data/files
collection = ns.apply_to_collection("docs") # tenant_tenant_abc_docs
key = ns.apply_to_key("cache:item")         # tenant_tenant_abc:cache:item
```

---

## RBAC

```python
from deerflow.enterprise import RBACEngine, Role, check_permission, require_permission

engine = RBACEngine()

# Check permission
if engine.check_permission("user_1", "agent:execute", tenant_id="tenant_abc"):
    # Allow execution
    pass

# Require permission (raises if denied)
engine.require_permission("user_1", "agent:admin", tenant_id="tenant_abc")
```

### Role Hierarchy

| Role | Permissions |
|------|-------------|
| `tenant_admin` | Full access within tenant |
| `project_manager` | Project-level management |
| `developer` | Create/edit agents |
| `operator` | Run/monitor |
| `external` | Limited read-only |

---

## Audit Logging

```python
from deerflow.enterprise import ImmutableAuditLog, AuditEvent, AuditEventType, AuditSigner

# Create audit log with signing
signer = AuditSigner()
audit_log = ImmutableAuditLog(signer=signer)

# Log event
event = AuditEvent(
    event_type=AuditEventType.PERMISSION_CHECK,
    tenant_id="tenant_abc",
    actor="user_1",
    action="agent:execute",
    resource="agent_research",
)
await audit_log.append(event)

# Verify chain integrity
is_valid = audit_log.verify_chain()
assert is_valid is True
```

---

## Approval Workflow

```python
from deerflow.enterprise import ApprovalRule, ApprovalRuleEngine, ApprovalMiddleware

engine = ApprovalRuleEngine()

# Register approval rules
engine.register_rule(ApprovalRule(
    name="financial_approval",
    condition=lambda tool_args: tool_args.get("tool") == "transfer_funds",
    approvers=["finance_manager", "cfo"],
    timeout_hours=24,
))

# Check if tool call requires approval
result = engine.check_rules({"tool": "transfer_funds", "amount": 50000})
if result:
    # Create approval request and suspend execution
    request = engine.create_request(
        tool_call={"tool": "transfer_funds", "amount": 50000},
        matched_rules=result,
        tenant_id="tenant_abc",
    )
```

---

## Agent Teams

```python
from deerflow.enterprise import TaskDecomposer, AgentTeamOrchestrator, ExecutionPlan

# Decompose complex task
decomposer = TaskDecomposer()
plan = await decomposer.decompose(
    goal="Build and deploy a web application",
    context={"language": "python", "framework": "fastapi"},
)

# Execute with agent team
orchestrator = AgentTeamOrchestrator(max_parallel=3)
result = await orchestrator.execute_plan(plan, tenant_id="tenant_abc")

# Access results
for task_result in result.subtask_results:
    print(f"Task {task_result.task_id}: {task_result.status}")
```

---

## Knowledge Base & RAG

```python
from deerflow.enterprise import CorporateKnowledgeBase, KnowledgeDocument, KnowledgeBaseConfig

# Configure knowledge base
config = KnowledgeBaseConfig(
    enabled=True,
    vector_store={"provider": "chroma", "collection_name": "kb"},
    chunking={"strategy": "paragraphs", "chunk_size": 1000},
    retrieval={"top_k": 5, "similarity_threshold": 0.7},
)

kb = CorporateKnowledgeBase(config)

# Add document
doc = KnowledgeDocument(
    doc_id="policy_001",
    title="Company Policy",
    content="Full document content...",
)
await kb.add_document(doc, tenant_id="tenant_abc")

# Search
chunks = await kb.search(
    query="What is the refund policy?",
    tenant_id="tenant_abc",
    top_k=5,
)
```

### RAG Middleware

```python
from deerflow.enterprise import KnowledgeRetrievalMiddleware

# Auto-injects relevant knowledge into LLM context
middleware = KnowledgeRetrievalMiddleware(
    enabled=True,
    knowledge_config=config,
)
```

---

## Brand Compliance

```python
from deerflow.enterprise import BrandController, BrandGuidelines

brand = BrandController(BrandGuidelines(
    brand_name="Acme Corp",
    forbidden_words=["competitor", "badword"],
    required_disclaimers=["Terms and conditions apply"],
    tone_guidelines="Professional and friendly",
))

result = await brand.review_content("Welcome to Acme Corp!")
if not result.approved:
    for issue in result.issues:
        print(f"[{issue.severity}] {issue.message}")
```

---

## Compliance Filtering

```python
from deerflow.enterprise import ComplianceFilter, SensitiveWordRule, ContentType

filter = ComplianceFilter(
    sensitive_words=["secret", "confidential"],
    policy_rules=[
        SensitiveWordRule(name="pii", words=["ssn", "password"], severity="block"),
    ],
    auto_review=True,
)

result = await filter.filter_output(
    "My password is secret123",
    ContentType.TEXT,
)

if result.blocked:
    print("Content blocked!")
for v in result.violations:
    print(f"[{v.severity}] {v.message}")

# Sanitized version available
if result.sanitized_content:
    print(result.sanitized_content)  # "My ******** is ******123"
```

---

## Enterprise Sandbox

```python
from deerflow.enterprise import EnterpriseSandboxProvider, AuditedSandbox

provider = EnterpriseSandboxProvider(
    base_provider=local_sandbox_provider,
    audit_log=audit_log,
    quota_manager=quota_manager,
)

# Acquire with quota check and audit
sandbox = await provider.acquire("thread_1", "tenant_abc")

# All operations are audited
result = await sandbox.execute_command("ls -la")
content = await sandbox.read_file("/path/to/file")
await sandbox.write_file("/path/to/file", "content")

# Release with audit
await provider.release(sandbox.id, "tenant_abc")
```

---

## Performance Optimizations

### Quota Cache

```python
from deerflow.enterprise.performance import QuotaCacheManager

cached_quota = QuotaCacheManager(
    quota_manager=quota_manager,
    ttl_seconds=30,
)

# First call hits Redis, subsequent calls use cache
quota = await cached_quota.get_quota("tenant_abc")
```

### Batched Audit Log

```python
from deerflow.enterprise.performance import BatchedAuditLog, AuditBatchConfig

batched = BatchedAuditLog(
    storage=immutable_audit_log,
    config=AuditBatchConfig(max_batch_size=100, max_wait_seconds=5.0),
)

# Events are buffered
await batched.log(event_type, details)

# Explicit flush
count = await batched.flush()
```

### Knowledge Base Query Cache

```python
from deerflow.enterprise.performance import KBQueryCache

kb_cache = KBQueryCache(ttl_seconds=300)

results = await kb_cache.get_or_query(
    kb=knowledge_base,
    query="refund policy",
    tenant_id="tenant_abc",
    top_k=5,
)
```

---

## Configuration Reference

```yaml
# Multi-tenancy
tenancy:
  enabled: false
  isolation_mode: "strict"  # strict | relaxed
  default_plan: "free"

# RBAC
rbac:
  enabled: false
  policy_file: ".deer-flow/rbac_policy.csv"

# Audit
audit:
  enabled: false
  storage_path: ".deer-flow/audit"
  signing_key: $AUDIT_SIGNING_KEY

# Quota
quota:
  enabled: false
  redis_url: "redis://localhost:6379"
  defaults:
    max_concurrent_sandboxes: 5
    max_api_calls_per_hour: 1000

# Approval
approval:
  enabled: false
  default_timeout_hours: 24
  storage_path: ".deer-flow/approvals"

# Knowledge Base
knowledge_base:
  enabled: false
  vector_store:
    provider: "chroma"
    collection_name: "deerflow_kb"
  embedding:
    provider: "openai"
    model: "text-embedding-3-small"
  chunking:
    strategy: "paragraphs"
    chunk_size: 1000
  retrieval:
    top_k: 5
    similarity_threshold: 0.7

# Brand
brand:
  enabled: false
  brand_name: ""
  forbidden_words: []
  required_disclaimers: []

# Compliance
compliance:
  enabled: false
  sensitive_words: []
  policy_rules: []
  auto_review: true
```
