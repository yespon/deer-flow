---
title: Enterprise Subsystem 1 - RBAC Middleware and Quota Management Design
description: Design specification for RBAC permission checking middleware and tenant quota management system
author: Claude Code
date: 2026-05-26
version: 1.0.0
---

# Enterprise Subsystem 1: RBAC Middleware and Quota Management

## Overview

This document specifies the implementation of RBACMiddleware and QuotaManagement for DeerFlow Enterprise, completing the Phase 1 infrastructure layer.

**Scope:**
- RBACMiddleware - Permission checking for tool calls
- QuotaManager - Tenant resource quota tracking
- QuotaMiddleware - Quota enforcement middleware

**Dependencies:**
- Existing `deerflow.enterprise.rbac` (RBACEngine, Role)
- Existing `deerflow.enterprise.tenancy` (get_current_tenant)
- Existing `deerflow.runtime.user_context` (get_effective_user_id)
- Redis for distributed counters

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    RBACMiddleware                            │
├─────────────────────────────────────────────────────────────┤
│  1. Extract user_id via get_effective_user_id()             │
│  2. Extract tenant_id via get_current_tenant()              │
│  3. Map tool_name → resource_type, action                   │
│  4. Call check_permission(user, tenant, resource, action)   │
│  5. Return error ToolMessage if denied                      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    QuotaMiddleware                           │
├─────────────────────────────────────────────────────────────┤
│  1. Check TenantQuota configuration                         │
│  2. Query current usage via QuotaManager                    │
│  3. Return QuotaExceeded error if over limit                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    QuotaManager                              │
├─────────────────────────────────────────────────────────────┤
│  - Redis-backed distributed counters                        │
│  - Per-tenant resource tracking                             │
│  - Automatic expiration and cleanup                         │
└─────────────────────────────────────────────────────────────┘
```

### Middleware Chain Integration

```python
# Recommended middleware order (Layer 1 infrastructure)
MIDDLEWARE_CHAIN = [
    TenantIdentificationMiddleware,    # Existing
    RBACMiddleware,                    # NEW
    QuotaMiddleware,                   # NEW
    # ... other middleware
]
```

---

## Detailed Design

### 2.1 RBACMiddleware

**File:** `backend/packages/harness/deerflow/enterprise/rbac_middleware.py`

**Responsibilities:**
- Intercept tool calls before execution
- Extract user identity and tenant context
- Map tool names to resource/action types
- Enforce permissions via RBACEngine
- Return structured error messages on denial

**Tool-to-Resource Mapping:**

| Tool Name Pattern | Resource Type | Action |
|-------------------|---------------|--------|
| `bash` | `sandbox` | `execute` |
| `str_replace` | `sandbox` | `execute` |
| `write_file` | `sandbox` | `execute` |
| `read_file` | `sandbox` | `read` |
| `ls` | `sandbox` | `read` |
| `task` | `agent` | `execute` |
| `ask_clarification` | `interaction` | `execute` |
| `view_image` | `file` | `read` |
| `present_files` | `file` | `read` |
| `setup_agent` | `agent` | `create` |
| `update_agent` | `agent` | `update` |

**Error Message Format:**
```
❌ Permission Denied

You don't have permission to execute 'bash' in this tenant.
Required: sandbox:execute
Your roles: [operator]
```

### 2.2 QuotaManager

**File:** `backend/packages/harness/deerflow/enterprise/quota.py`

**Responsibilities:**
- Manage per-tenant resource quotas
- Track concurrent resource usage via Redis
- Provide atomic acquire/release operations
- Support quota queries and monitoring

**Redis Key Schema:**
```
quota:{tenant_id}:{resource}  # Counter (e.g., quota:tenant_123:concurrent_sandboxes)
quota:{tenant_id}:config      # Hash of quota limits
```

**Resource Types:**
- `concurrent_sandboxes` - Active sandbox count
- `daily_api_calls` - API call rate limiting
- `storage_bytes` - Storage usage

### 2.3 QuotaMiddleware

**File:** `backend/packages/harness/deerflow/enterprise/quota_middleware.py`

**Responsibilities:**
- Check quota before sandbox acquisition
- Track usage for sandbox lifecycle
- Return quota exceeded errors

**Integration Points:**
- Hooks into SandboxMiddleware lifecycle
- Tracks sandbox acquire/release

---

## Configuration

### QuotaConfig Schema

```python
class QuotaConfig(BaseModel):
    enabled: bool = False
    redis_url: str = "redis://localhost:6379"
    default_quotas: TenantQuota = Field(default_factory=TenantQuota)
    enforcement_mode: Literal["hard", "soft"] = "hard"
```

### AppConfig Integration

```python
# Add to AppConfig
quota: QuotaConfig = Field(default_factory=QuotaConfig)
```

---

## Error Handling

### PermissionDeniedError

Raised when RBAC check fails. Caught by middleware and converted to ToolMessage.

### QuotaExceededError

Raised when quota limit reached. Contains:
- `resource`: The exceeded resource type
- `limit`: The configured limit
- `current`: Current usage
- `tenant_id`: Affected tenant

---

## Testing Strategy (TDD)

### Test Files

```
backend/tests/enterprise/
├── test_rbac_middleware.py      # 8 test cases
├── test_quota_manager.py        # 10 test cases
└── test_quota_middleware.py     # 6 test cases
```

### RBACMiddleware Tests

1. `test_allows_permitted_tool_call` - Operator can read files
2. `test_denies_unpermitted_tool_call` - External cannot execute bash
3. `test_extracts_user_from_context` - Correct user extraction
4. `test_extracts_tenant_from_context` - Correct tenant extraction
5. `test_maps_tool_name_to_resource` - Correct resource mapping
6. `test_returns_error_tool_message_on_denial` - Proper error format
7. `test_skips_check_when_rbac_disabled` - Config bypass
8. `test_handles_missing_user_gracefully` - Default to restricted

### QuotaManager Tests

1. `test_acquire_succeeds_when_under_limit` - Normal acquisition
2. `test_acquire_fails_when_at_limit` - Limit enforcement
3. `test_release_decrements_counter` - Proper cleanup
4. `test_usage_accurately_tracked` - Counter accuracy
5. `test_counters_expire_correctly` - TTL handling
6. `test_get_usage_returns_current_value` - Query API
7. `test_multiple_resources_independent` - Isolation
8. `test_acquire_multiple_atomically` - Batch operations
9. `test_handles_redis_unavailable` - Graceful degradation
10. `test_config_override_per_tenant` - Custom quotas

### QuotaMiddleware Tests

1. `test_allows_sandbox_when_quota_available` - Normal flow
2. `test_blocks_sandbox_when_quota_exhausted` - Enforcement
3. `test_tracks_usage_accurately` - Lifecycle tracking
4. `test_returns_error_message_with_details` - Error format
5. `test_skips_when_quota_disabled` - Config bypass
6. `test_handles_acquire_release_cycle` - Full lifecycle

---

## Implementation Order

1. **QuotaConfig** - Configuration models
2. **QuotaManager** - Core quota tracking (with tests)
3. **QuotaMiddleware** - Integration layer (with tests)
4. **RBACMiddleware** - Permission checking (with tests)
5. **Integration** - Wire into middleware chain
6. **Documentation** - Update CLAUDE.md and README

---

## Acceptance Criteria

- [ ] All 24 unit tests pass
- [ ] RBACMiddleware blocks unauthorized tool calls
- [ ] QuotaMiddleware enforces resource limits
- [ ] Error messages are clear and actionable
- [ ] No regressions in existing tests (`make test` passes)
- [ ] Documentation updated with new middleware

---

*Design approved for implementation.*
