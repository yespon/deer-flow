# 后端能力与前后端交互优化设计文档

**日期**: 2026-05-30  
**版本**: 1.0  
**作者**: Claude + yespon  
**状态**: 设计阶段

---

## 1. 文档概述

### 1.1 背景
DeerFlow 是一个基于 LangGraph 的 AI Agent 系统，采用前后端分离架构。经过审查，发现了一些可以优化的地方，以提升系统稳定性、移动端体验和开发者体验。

### 1.2 目标
- 提升移动端用户体验
- 增强系统可靠性
- 改善错误处理能力
- 优化前后端数据一致性

### 1.3 范围
- Gateway API 层优化
- 前端 API 客户端改进
- 移动端适配增强
- 错误处理标准化

---

## 2. 当前架构回顾

### 2.1 系统架构

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Frontend  │──────▶│    Nginx     │──────▶│   Gateway   │
│  (Next.js)  │      │   (Port 2026)│      │  (Port 8001)│
└─────────────┘      └──────────────┘      └──────┬──────┘
                                                   │
                          ┌────────────────────────┼────────────────────────┐
                          │                        │                        │
                          ▼                        ▼                        ▼
                   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
                   │  LangGraph  │         │  Sandbox    │         │  Memory     │
                   │   Runtime   │         │  (Local/AIO)│         │   Store     │
                   └─────────────┘         └─────────────┘         └─────────────┘
```

### 2.2 现有端点清单

| 路由 | 端点 | 用途 |
|------|------|------|
| `/api/models` | GET | 模型列表 |
| `/api/threads/{id}/runs` | POST/GET | 运行管理 |
| `/api/threads/{id}/runs/stream` | POST | SSE 流 |
| `/api/threads/{id}/messages` | GET | 消息历史 |
| `/api/threads/{id}/uploads` | POST | 文件上传 |
| `/api/agents` | CRUD | 自定义 Agent |
| `/api/mcp` | GET/PUT | MCP 配置 |
| `/api/memory` | GET/POST | 记忆管理 |

---

## 3. 发现的问题

### 3.1 问题分类

| 优先级 | 问题 | 影响 | 状态 |
|--------|------|------|------|
| P0 | Thread 删除后本地数据残留 | 数据一致性 | 待修复 |
| P0 | SSE 移动端重连不稳定 | 用户体验 | 待修复 |
| P1 | API 错误格式不统一 | 开发体验 | 待修复 |
| P1 | 缺少健康检查端点 | 可观测性 | 待添加 |
| P2 | 文件上传无分片支持 | 大文件上传 | 待优化 |
| P2 | 缺少 API 版本控制 | 兼容性 | 待规划 |

### 3.2 详细问题描述

#### 3.2.1 Thread 删除不完整

**现象**: 调用 `DELETE /api/threads/{id}` 后，LangGraph 的 thread 被删除，但本地 `.deer-flow/threads/{id}` 目录可能残留。

**影响**: 长期运行后产生 orphaned 数据，占用磁盘空间。

**根因**: 删除操作未完全清理本地文件系统数据。

#### 3.2.2 SSE 移动端重连问题

**现象**: 移动设备在切换网络或锁屏后，SSE 连接中断且无法自动恢复。

**影响**: 用户需要手动刷新页面才能继续对话。

**根因**: 
- 前端缺乏智能重连机制
- 后端不支持从断点恢复流

#### 3.2.3 API 错误格式不一致

**现象**: 不同端点返回的错误格式各异，有的是字符串，有的是对象。

**影响**: 前端错误处理复杂，用户体验不一致。

**示例**:
```json
// 端点 A 错误格式
{ "error": "Thread not found" }

// 端点 B 错误格式  
{ "detail": "Run is not active", "status": 409 }

// 端点 C 错误格式
"Internal server error"
```

---

## 4. 设计方案

### 4.1 统一错误响应格式

#### 4.1.1 错误响应标准

所有 API 错误响应应遵循以下格式：

```json
{
  "error": {
    "code": "THREAD_NOT_FOUND",
    "message": "The requested thread does not exist",
    "details": {
      "thread_id": "abc-123",
      "suggestion": "Create a new thread to start a conversation"
    },
    "request_id": "req_20240530_001",
    "timestamp": "2026-05-30T12:00:00Z"
  }
}
```

#### 4.1.2 错误码规范

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| `THREAD_NOT_FOUND` | 404 | Thread 不存在 |
| `RUN_NOT_FOUND` | 404 | Run 不存在 |
| `RUN_NOT_CANCELLABLE` | 409 | Run 无法取消 |
| `INVALID_AGENT_NAME` | 422 | Agent 名称无效 |
| `AGENT_ALREADY_EXISTS` | 409 | Agent 已存在 |
| `UPLOAD_TOO_LARGE` | 413 | 文件过大 |
| `RATE_LIMIT_EXCEEDED` | 429 | 速率限制 |
| `INTERNAL_ERROR` | 500 | 内部错误 |

#### 4.1.3 FastAPI 异常处理实现

```python
# backend/app/gateway/exceptions.py
from fastapi import Request
from fastapi.responses import JSONResponse
from typing import Any, Optional
import time
import uuid

class APIError(Exception):
    """Base API error with structured response."""
    
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: Optional[dict] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}

class ThreadNotFoundError(APIError):
    def __init__(self, thread_id: str):
        super().__init__(
            code="THREAD_NOT_FOUND",
            message=f"Thread '{thread_id}' not found",
            status_code=404,
            details={"thread_id": thread_id}
        )

async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Global API error handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": str(uuid.uuid4())[:8],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        }
    )
```

### 4.2 SSE 重连机制优化

#### 4.2.1 服务端支持

实现 SSE 流断点续传：

```python
# backend/app/gateway/routers/thread_runs.py

@router.get("/{thread_id}/runs/{run_id}/stream")
async def stream_run_with_resume(
    thread_id: str,
    run_id: str,
    last_event_id: Optional[str] = Query(None, description="Last received event ID for resume"),
    request: Request
) -> StreamingResponse:
    """Stream with support for resuming from a specific event."""
    
    run_mgr = get_run_manager(request)
    record = await run_mgr.get(run_id)
    
    if record is None:
        raise ThreadNotFoundError(thread_id)
    
    # If last_event_id provided, skip events up to that point
    if last_event_id:
        buffered_events = await run_mgr.get_events_after(run_id, last_event_id)
        return StreamingResponse(
            replay_then_stream(buffered_events, record),
            media_type="text/event-stream"
        )
    
    return StreamingResponse(
        sse_consumer(bridge, record, request, run_mgr),
        media_type="text/event-stream"
    )
```

#### 4.2.2 客户端重连实现

```typescript
// frontend/src/core/api/stream-resilient.ts

interface ResilientStreamOptions {
  threadId: string;
  runId: string;
  onEvent: (event: StreamEvent) => void;
  onError: (error: Error) => void;
  maxRetries?: number;
  baseDelay?: number;
}

class ResilientEventSource {
  private eventSource: EventSource | null = null;
  private lastEventId: string | null = null;
  private retryCount = 0;
  private maxRetries: number;
  private baseDelay: number;
  private abortController = new AbortController();

  constructor(private options: ResilientStreamOptions) {
    this.maxRetries = options.maxRetries ?? 5;
    this.baseDelay = options.baseDelay ?? 1000;
  }

  async connect(): Promise<void> {
    const url = this.buildUrl();
    this.eventSource = new EventSource(url);
    
    this.eventSource.onmessage = (event) => {
      this.lastEventId = event.lastEventId;
      this.retryCount = 0; // Reset on successful message
      this.options.onEvent(JSON.parse(event.data));
    };

    this.eventSource.onerror = (error) => {
      this.handleError(error);
    };
  }

  private handleError(error: Event): void {
    this.eventSource?.close();
    
    if (this.retryCount >= this.maxRetries) {
      this.options.onError(new Error('Max retries exceeded'));
      return;
    }

    // Exponential backoff with jitter
    const delay = this.calculateBackoff();
    this.retryCount++;

    setTimeout(() => this.connect(), delay);
  }

  private calculateBackoff(): number {
    const exponential = this.baseDelay * Math.pow(2, this.retryCount);
    const jitter = Math.random() * 1000;
    return Math.min(exponential + jitter, 30000); // Cap at 30s
  }

  private buildUrl(): string {
    const params = new URLSearchParams();
    if (this.lastEventId) {
      params.set('last_event_id', this.lastEventId);
    }
    return `/api/threads/${this.options.threadId}/runs/${this.options.runId}/stream?${params}`;
  }

  disconnect(): void {
    this.abortController.abort();
    this.eventSource?.close();
  }
}
```

### 4.3 Thread 清理完善

#### 4.3.1 服务端实现

```python
# backend/app/gateway/routers/threads.py

@router.delete("/{thread_id}")
@require_permission("threads", "delete", owner_check=True)
async def delete_thread(
    thread_id: str,
    request: Request,
    cleanup_data: bool = Query(default=True, description="Also delete local thread data")
) -> Response:
    """Delete thread with complete cleanup.
    
    Steps:
    1. Cancel any active runs
    2. Delete from LangGraph
    3. Clean up local files (if cleanup_data=true)
    4. Remove from run store
    """
    run_mgr = get_run_manager(request)
    user_id = await get_current_user(request)
    
    # Step 1: Cancel active runs
    active_runs = await run_mgr.list_by_thread(thread_id, user_id=user_id)
    for run in active_runs:
        if run.status in (RunStatus.pending, RunStatus.running):
            await run_mgr.cancel(run.run_id, action="interrupt")
    
    # Step 2: Delete from LangGraph
    checkpointer = get_checkpointer(request)
    await checkpointer.adelete({"configurable": {"thread_id": thread_id}})
    
    # Step 3: Clean up local data
    if cleanup_data:
        paths = get_paths()
        thread_dir = paths.user_thread_dir(user_id, thread_id)
        if thread_dir.exists():
            shutil.rmtree(thread_dir)
    
    # Step 4: Clean up run records
    await run_mgr.delete_by_thread(thread_id)
    
    return Response(status_code=204)
```

### 4.4 健康检查端点

#### 4.4.1 健康检查实现

```python
# backend/app/gateway/routers/health.py

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Literal
import asyncio

router = APIRouter(prefix="/api/health", tags=["health"])

class HealthStatus(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    components: dict[str, ComponentHealth]
    timestamp: str

class ComponentHealth(BaseModel):
    status: Literal["up", "down", "degraded"]
    latency_ms: float
    details: dict | None = None

@router.get("", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """Comprehensive health check endpoint.
    
    Checks:
    - LangGraph runtime connectivity
    - Database/checkpointer availability
    - Sandbox provider status
    - Memory store accessibility
    """
    components = {}
    overall_status = "healthy"
    
    # Check LangGraph
    try:
        start = time.time()
        await check_langgraph_health()
        components["langgraph"] = ComponentHealth(
            status="up",
            latency_ms=(time.time() - start) * 1000
        )
    except Exception as e:
        components["langgraph"] = ComponentHealth(
            status="down",
            latency_ms=0,
            details={"error": str(e)}
        )
        overall_status = "unhealthy"
    
    # Check sandbox
    try:
        start = time.time()
        await check_sandbox_health()
        components["sandbox"] = ComponentHealth(
            status="up", 
            latency_ms=(time.time() - start) * 1000
        )
    except Exception as e:
        components["sandbox"] = ComponentHealth(
            status="down",
            latency_ms=0,
            details={"error": str(e)}
        )
        overall_status = "degraded"
    
    return HealthStatus(
        status=overall_status,
        version=get_version(),
        components=components,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )

@router.get("/ready")
async def readiness_check() -> dict:
    """Kubernetes-style readiness probe."""
    return {"ready": True}

@router.get("/live")
async def liveness_check() -> dict:
    """Kubernetes-style liveness probe."""
    return {"alive": True}
```

### 4.5 文件上传分片支持

#### 4.5.1 分片上传设计

```python
# backend/app/gateway/routers/uploads.py

from fastapi import UploadFile, BackgroundTasks

@router.post("/{thread_id}/uploads/initiate")
async def initiate_upload(
    thread_id: str,
    filename: str,
    total_size: int,
    chunk_size: int = Query(default=5 * 1024 * 1024)  # 5MB default
) -> dict:
    """Initiate a multipart upload session.
    
    Returns upload session ID and presigned URLs for each chunk.
    """
    upload_id = generate_upload_id()
    total_chunks = (total_size + chunk_size - 1) // chunk_size
    
    # Create upload session record
    session = UploadSession(
        id=upload_id,
        thread_id=thread_id,
        filename=filename,
        total_size=total_size,
        chunk_size=chunk_size,
        total_chunks=total_chunks,
        received_chunks=set()
    )
    await save_upload_session(session)
    
    return {
        "upload_id": upload_id,
        "chunk_size": chunk_size,
        "total_chunks": total_chunks,
        "upload_urls": [
            f"/api/threads/{thread_id}/uploads/{upload_id}/chunks/{i}"
            for i in range(total_chunks)
        ]
    }

@router.put("/{thread_id}/uploads/{upload_id}/chunks/{chunk_index}")
async def upload_chunk(
    thread_id: str,
    upload_id: str,
    chunk_index: int,
    file: UploadFile
) -> dict:
    """Upload a single chunk."""
    session = await get_upload_session(upload_id)
    
    # Save chunk to temp location
    chunk_path = get_chunk_path(upload_id, chunk_index)
    with open(chunk_path, "wb") as f:
        f.write(await file.read())
    
    session.received_chunks.add(chunk_index)
    await save_upload_session(session)
    
    # Check if all chunks received
    if len(session.received_chunks) == session.total_chunks:
        await finalize_upload(session)
    
    return {
        "upload_id": upload_id,
        "chunk_index": chunk_index,
        "received": len(session.received_chunks),
        "total": session.total_chunks,
        "complete": len(session.received_chunks) == session.total_chunks
    }
```

---

## 5. 前端适配

### 5.1 错误处理适配

```typescript
// frontend/src/core/api/error-handler.ts

interface APIError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  request_id: string;
  timestamp: string;
}

class APIErrorHandler {
  static handle(error: APIError): void {
    // Log to monitoring service
    console.error(`[${error.request_id}] ${error.code}: ${error.message}`);
    
    // Show user-friendly message
    const userMessage = this.getUserMessage(error);
    showToast(userMessage, 'error');
    
    // Handle specific errors
    switch (error.code) {
      case 'THREAD_NOT_FOUND':
        redirectTo('/workspace/chats/new');
        break;
      case 'RATE_LIMIT_EXCEEDED':
        showRetryDialog(error.details?.retry_after);
        break;
    }
  }

  private static getUserMessage(error: APIError): string {
    const messages: Record<string, string> = {
      'THREAD_NOT_FOUND': '对话不存在，已为您创建新对话',
      'RUN_NOT_CANCELLABLE': '运行无法取消，可能已结束',
      'UPLOAD_TOO_LARGE': '文件过大，请分批上传',
      'RATE_LIMIT_EXCEEDED': '请求过于频繁，请稍后再试',
    };
    return messages[error.code] || error.message;
  }
}
```

### 5.2 移动端网络状态监测

```typescript
// frontend/src/hooks/use-network-status.ts

import { useEffect, useState } from 'react';

export function useNetworkStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [connectionType, setConnectionType] = useState<string>('unknown');

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Monitor connection type (mobile networks)
    const connection = (navigator as any).connection;
    if (connection) {
      const updateConnection = () => {
        setConnectionType(connection.effectiveType);
      };
      connection.addEventListener('change', updateConnection);
      updateConnection();

      return () => {
        window.removeEventListener('online', handleOnline);
        window.removeEventListener('offline', handleOffline);
        connection.removeEventListener('change', updateConnection);
      };
    }

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return { isOnline, connectionType };
}
```

---

## 6. 实施计划

### 6.1 优先级和依赖

```
Phase 1 (P0 - 2周):
  ├── 统一错误响应格式
  ├── Thread 删除完善
  └── SSE 断点续传服务端

Phase 2 (P1 - 2周):
  ├── SSE 客户端重连机制
  ├── 健康检查端点
  └── 前端错误处理适配

Phase 3 (P2 - 1周):
  ├── 文件分片上传
  └── API 版本控制规划
```

### 6.2 测试策略

| 测试类型 | 覆盖范围 | 工具 |
|----------|----------|------|
| 单元测试 | 错误处理、重连逻辑 | pytest, vitest |
| 集成测试 | API 端点 | pytest + TestClient |
| E2E 测试 | 完整用户流程 | Playwright |
| 性能测试 | SSE 并发 | k6 |

---

## 7. 附录

### 7.1 变更日志

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-05-30 | 1.0 | 初始版本 |

### 7.2 参考文档

- [LangGraph Platform API](https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref.html)
- [FastAPI Exception Handling](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [SSE Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html)

---

## 8. 审批

| 角色 | 姓名 | 状态 | 日期 |
|------|------|------|------|
| 作者 | yespon | ✅ | 2026-05-30 |
| 审查 | Claude | ✅ | 2026-05-30 |
| 批准 | TBD | ⏳ | - |
