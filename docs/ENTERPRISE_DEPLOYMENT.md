# DeerFlow Enterprise Deployment Guide

## Architecture Overview

DeerFlow Enterprise is deployed as a single application instance with the following infrastructure dependencies:

```
┌─────────────────────────────────────────────────────┐
│                 DeerFlow Gateway (8001)              │
│  ┌───────────┬───────────┬───────────┬────────────┐  │
│  │ REST API  │ Agent     │ Enterprise│ Channels   │  │
│  │ Routers   │ Runtime   │ Middleware│ (IM)       │  │
│  └───────────┴───────────┴───────────┴────────────┘  │
├─────────────────────────────────────────────────────┤
│                    Storage Layer                      │
│  ┌──────────┬──────────┬──────────┬────────────────┐ │
│  │PostgreSQL│  Redis   │  Chroma  │ Object Store   │ │
│  │ (State)  │ (Quota)  │  (RAG)   │ (Files)        │ │
│  └──────────┴──────────┴──────────┴────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## Prerequisites

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.12+ | Runtime |
| PostgreSQL | 15+ | State persistence, audit logs |
| Redis | 7+ | Quota counters, caching |
| Chroma / Milvus | Latest | Vector store for RAG |

## Quick Start

### 1. Enable Enterprise Features

Copy and edit configuration:

```bash
cp config.example.yaml config.yaml
```

Enable enterprise modules in `config.yaml`:

```yaml
tenancy:
  enabled: true
  isolation_mode: "strict"

rbac:
  enabled: true

audit:
  enabled: true
  signing_key: $AUDIT_SIGNING_KEY

quota:
  enabled: true
  redis_url: "redis://localhost:6379"

knowledge_base:
  enabled: true
  vector_store:
    provider: "chroma"
    collection_name: "deerflow_kb"
  embedding:
    provider: "openai"
    model: "text-embedding-3-small"
    api_key: $OPENAI_API_KEY

brand:
  enabled: true
  brand_name: "Your Company"
  forbidden_words: ["competitor_name"]

compliance:
  enabled: true
  sensitive_words: ["secret", "confidential"]
```

### 2. Set Environment Variables

```bash
export AUDIT_SIGNING_KEY="your-ed25519-private-key"
export OPENAI_API_KEY="sk-..."
export REDIS_URL="redis://localhost:6379"
```

### 3. Start Services

```bash
# Start infrastructure
docker compose up -d postgres redis chroma

# Start DeerFlow
make dev
```

---

## Production Deployment

### Docker Compose

```yaml
version: "3.8"
services:
  gateway:
    build: .
    ports:
      - "8001:8001"
    environment:
      - DEER_FLOW_CONFIG_PATH=/app/config.yaml
      - AUDIT_SIGNING_KEY=${AUDIT_SIGNING_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://deerflow:password@postgres:5432/deerflow
    depends_on:
      - postgres
      - redis
      - chroma

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: deerflow
      POSTGRES_USER: deerflow
      POSTGRES_PASSWORD: password
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redisdata:/data

  chroma:
    image: chromadb/chroma:latest
    volumes:
      - chromadata:/chroma/chroma

  nginx:
    image: nginx:alpine
    ports:
      - "2026:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - gateway

volumes:
  pgdata:
  redisdata:
  chromadata:
```

### Kubernetes

For production Kubernetes deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: deerflow-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: deerflow-gateway
  template:
    metadata:
      labels:
        app: deerflow-gateway
    spec:
      containers:
        - name: gateway
          image: deerflow-enterprise:latest
          ports:
            - containerPort: 8001
          env:
            - name: AUDIT_SIGNING_KEY
              valueFrom:
                secretKeyRef:
                  name: deerflow-secrets
                  key: audit-signing-key
            - name: REDIS_URL
              value: "redis://redis-master:6379"
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "2000m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8001
            initialDelaySeconds: 30
            periodSeconds: 10
```

---

## Scaling Considerations

### Horizontal Scaling

| Component | Scaling Strategy |
|-----------|-----------------|
| Gateway | Stateless, scale horizontally behind load balancer |
| PostgreSQL | Primary-replica with read replicas |
| Redis | Cluster mode for quota counters |
| Chroma | Separate service, scale read replicas |

### Performance Tuning

**Quota Cache**: Set `ttl_seconds` based on your tolerance for stale data.

```python
from deerflow.enterprise.performance import QuotaCacheManager

# 30-second TTL reduces Redis load significantly
cached = QuotaCacheManager(quota_manager, ttl_seconds=30)
```

**Audit Batching**: Buffer audit events for batch writes.

```python
from deerflow.enterprise.performance import BatchedAuditLog, AuditBatchConfig

batched = BatchedAuditLog(
    storage=audit_log,
    config=AuditBatchConfig(max_batch_size=100, max_wait_seconds=5.0),
)
```

**KB Query Cache**: Cache frequent queries.

```python
from deerflow.enterprise.performance import KBQueryCache

# 5-minute TTL for knowledge base queries
kb_cache = KBQueryCache(ttl_seconds=300)
```

---

## Monitoring

### Key Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|----------------|
| `quota.cache.hit_rate` | Quota cache efficiency | < 70% |
| `audit.batch.size` | Audit batch flush size | > 80 |
| `kb.cache.hit_rate` | Knowledge base cache efficiency | < 60% |
| `approval.pending_count` | Pending approval requests | > 50 |
| `sandbox.concurrent` | Active sandbox count | > 80% of quota |

### Health Checks

```bash
# Gateway health
curl http://localhost:8001/health

# Redis connectivity
redis-cli -h localhost ping

# Chroma connectivity
curl http://localhost:8000/api/v1/heartbeat
```

---

## Security Checklist

- [ ] Audit signing key stored in vault (not env var in production)
- [ ] Redis requires authentication
- [ ] PostgreSQL uses SSL connections
- [ ] API keys rotated every 90 days
- [ ] RBAC policy reviewed quarterly
- [ ] Tenant isolation verified with integration tests
- [ ] Compliance filter rules updated for new regulations
- [ ] Brand guidelines reviewed after rebranding
- [ ] Audit log chain integrity verified weekly
- [ ] Sensitive word lists updated for new data types

---

## Troubleshooting

### Common Issues

**Quota exceeded errors**: Check Redis connectivity and quota cache TTL.

**Audit log integrity failure**: Verify signing key matches across instances.

**Knowledge base slow queries**: Increase `top_k` threshold or add query cache.

**Tenant isolation breach**: Verify namespace configuration and run isolation tests.

### Logs

```bash
# Enterprise module logs
grep "deerflow.enterprise" /var/log/deerflow/gateway.log

# Audit events
grep "audit" /var/log/deerflow/gateway.log | tail -100

# Quota operations
grep "quota" /var/log/deerflow/gateway.log | tail -100
```
