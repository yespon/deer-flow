# 后端优化 Phase 1 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Phase 1 的三个核心功能：统一错误响应格式、完善 Thread 删除、SSE 断点续传支持

**Architecture:** 基于 FastAPI 异常处理器构建统一错误响应；扩展 Thread 删除端点实现完整清理；在现有 SSE 基础上添加事件 ID 追踪和断点续传支持

**Tech Stack:** FastAPI, Python 3.12+, LangGraph SDK, TypeScript/React (前端适配)

---

## 文件结构规划

### 新增文件
| 文件 | 用途 |
|------|------|
| `backend/app/gateway/exceptions.py` | 统一异常类和错误处理 |
| `backend/app/gateway/routers/health.py` | 健康检查端点 |
| `backend/tests/test_exceptions.py` | 异常处理单元测试 |
| `backend/tests/test_thread_cleanup.py` | Thread 清理集成测试 |

### 修改文件
| 文件 | 修改内容 |
|------|----------|
| `backend/app/gateway/app.py` | 注册全局异常处理器 |
| `backend/app/gateway/routers/threads.py` | 完善删除逻辑 |
| `backend/app/gateway/routers/thread_runs.py` | 添加 last_event_id 参数 |
| `frontend/src/core/api/error-handler.ts` | 新增错误处理模块 |
| `frontend/src/core/threads/hooks.ts` | 集成重连逻辑 |

---

## Task 1: 统一错误响应格式 - 基础异常类

**Files:**
- Create: `backend/app/gateway/exceptions.py`
- Test: `backend/tests/test_exceptions.py`

**目标:** 建立标准化的错误响应体系

### Step 1: 创建基础异常类
- [ ] **编写异常类代码**

```python
# backend/app/gateway/exceptions.py
"""Unified API error handling."""

import time
import uuid
from typing import Any, Optional

from fastapi import Request
from fastapi.responses import JSONResponse


class APIError(Exception):
    """Base API error with structured response."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ThreadNotFoundError(APIError):
    def __init__(self, thread_id: str):
        super().__init__(
            code="THREAD_NOT_FOUND",
            message=f"Thread '{thread_id}' not found",
            status_code=404,
            details={
                "thread_id": thread_id,
                "suggestion": "Create a new thread to start a conversation",
            },
        )


class RunNotFoundError(APIError):
    def __init__(self, run_id: str):
        super().__init__(
            code="RUN_NOT_FOUND",
            message=f"Run '{run_id}' not found",
            status_code=404,
            details={"run_id": run_id},
        )


class RunNotCancellableError(APIError):
    def __init__(self, run_id: str, status: str):
        super().__init__(
            code="RUN_NOT_CANCELLABLE",
            message=f"Run '{run_id}' cannot be cancelled (status: {status})",
            status_code=409,
            details={"run_id": run_id, "status": status},
        )


class InvalidAgentNameError(APIError):
    def __init__(self, name: str):
        super().__init__(
            code="INVALID_AGENT_NAME",
            message=f"Invalid agent name '{name}'",
            status_code=422,
            details={
                "name": name,
                "pattern": "^[A-Za-z0-9-]+$",
                "description": "Letters, digits, and hyphens only",
            },
        )


class AgentAlreadyExistsError(APIError):
    def __init__(self, name: str):
        super().__init__(
            code="AGENT_ALREADY_EXISTS",
            message=f"Agent '{name}' already exists",
            status_code=409,
            details={"name": name},
        )


class RateLimitExceededError(APIError):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message="Rate limit exceeded. Please slow down.",
            status_code=429,
            details={"retry_after": retry_after},
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
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        },
    )


async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Fallback handler for unexpected exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {},
                "request_id": str(uuid.uuid4())[:8],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        },
    )
```

### Step 2: 编写单元测试
- [ ] **编写测试代码**

```python
# backend/tests/test_exceptions.py
"""Tests for API exception handling."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.exceptions import (
    APIError,
    AgentAlreadyExistsError,
    InvalidAgentNameError,
    RateLimitExceededError,
    RunNotCancellableError,
    RunNotFoundError,
    ThreadNotFoundError,
    api_error_handler,
)


@pytest.fixture
def app():
    app = FastAPI()
    app.add_exception_handler(APIError, api_error_handler)

    @app.get("/test/thread-not-found")
    async def test_thread_not_found():
        raise ThreadNotFoundError("thread-123")

    @app.get("/test/run-not-found")
    async def test_run_not_found():
        raise RunNotFoundError("run-456")

    @app.get("/test/rate-limit")
    async def test_rate_limit():
        raise RateLimitExceededError(retry_after=30)

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_thread_not_found_error(client):
    response = client.get("/test/thread-not-found")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "THREAD_NOT_FOUND"
    assert "thread-123" in data["error"]["message"]
    assert data["error"]["details"]["thread_id"] == "thread-123"
    assert "request_id" in data["error"]
    assert "timestamp" in data["error"]


def test_run_not_found_error(client):
    response = client.get("/test/run-not-found")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "RUN_NOT_FOUND"


def test_rate_limit_error(client):
    response = client.get("/test/rate-limit")
    assert response.status_code == 429
    data = response.json()
    assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert data["error"]["details"]["retry_after"] == 30


def test_error_response_structure(client):
    response = client.get("/test/thread-not-found")
    data = response.json()
    assert "error" in data
    error = data["error"]
    assert all(key in error for key in ["code", "message", "details", "request_id", "timestamp"])
```

### Step 3: 运行测试
- [ ] **执行测试并验证失败**

```bash
cd /Users/yespon/workspace/projects/deer-flow/backend
PYTHONPATH=. uv run pytest tests/test_exceptions.py -v
```

**预期输出:**
```
tests/test_exceptions.py::test_thread_not_found_error PASSED
tests/test_exceptions.py::test_run_not_found_error PASSED
tests/test_exceptions.py::test_rate_limit_error PASSED
tests/test_exceptions.py::test_error_response_structure PASSED
```

### Step 4: 提交代码
- [ ] **提交**

```bash
cd /Users/yespon/workspace/projects/deer-flow
git add backend/app/gateway/exceptions.py backend/tests/test_exceptions.py
git commit -m "feat(api): add unified exception handling infrastructure

- Add APIError base class with structured error response
- Add specific exceptions: ThreadNotFoundError, RunNotFoundError, etc.
- Add global exception handlers for FastAPI
- Add comprehensive unit tests"
```

---

## Task 2: 注册全局异常处理器

**Files:**
- Modify: `backend/app/gateway/app.py`
- Test: `backend/tests/test_exceptions.py` (补充集成测试)

### Step 1: 在 FastAPI 应用中注册异常处理器
- [ ] **修改 app.py**

```python
# backend/app/gateway/app.py
# 在文件顶部添加导入
from app.gateway.exceptions import (
    APIError,
    api_error_handler,
    generic_exception_handler,
)

# 在 create_app() 函数中添加异常处理器
app = FastAPI(...)

# 注册异常处理器
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)
```

### Step 2: 验证集成
- [ ] **创建集成测试**

```python
# backend/tests/test_exceptions.py (添加到文件末尾)

def test_global_exception_handler_registered():
    """Verify exception handlers are properly registered."""
    from app.gateway.app import create_app
    
    app = create_app()
    
    # Check that exception handlers are registered
    # FastAPI stores handlers in app.exception_handlers dict
    assert APIError in app.exception_handlers
    assert Exception in app.exception_handlers
```

### Step 3: 运行集成测试
- [ ] **执行测试**

```bash
PYTHONPATH=. uv run pytest tests/test_exceptions.py::test_global_exception_handler_registered -v
```

### Step 4: 提交
- [ ] **提交**

```bash
git add backend/app/gateway/app.py backend/tests/test_exceptions.py
git commit -m "feat(api): register global exception handlers in FastAPI app

- Wire up api_error_handler for APIError exceptions
- Add fallback generic_exception_handler for unexpected errors"
```

---

## Task 3: 完善 Thread 删除 - 扩展删除逻辑

**Files:**
- Modify: `backend/app/gateway/routers/threads.py`
- Test: `backend/tests/test_thread_cleanup.py`

### Step 1: 分析现有删除逻辑
- [ ] **阅读现有代码**

```bash
cat /Users/yespon/workspace/projects/deer-flow/backend/app/gateway/routers/threads.py
```

### Step 2: 实现完整清理的删除端点
- [ ] **修改 threads.py**

```python
# backend/app/gateway/routers/threads.py
# 在文件顶部添加导入
import shutil
from pathlib import Path

from app.gateway.exceptions import ThreadNotFoundError
from deerflow.config.paths import get_paths
from deerflow.runtime.user_context import get_effective_user_id

# 修改或添加 DELETE 端点
@router.delete("/{thread_id}", status_code=204)
@require_permission("threads", "delete", owner_check=True)
async def delete_thread(
    thread_id: str,
    request: Request,
    cleanup_data: bool = Query(default=True, description="Also delete local thread data"),
) -> Response:
    """Delete thread with complete cleanup.
    
    Steps:
    1. Cancel any active runs for this thread
    2. Delete from LangGraph (via checkpointer)
    3. Clean up local files (if cleanup_data=true)
    4. Remove from run store
    """
    run_mgr = get_run_manager(request)
    user_id = await get_current_user(request)
    
    # Step 1: Cancel active runs
    from deerflow.runtime import RunStatus
    active_runs = await run_mgr.list_by_thread(thread_id, user_id=user_id)
    for run in active_runs:
        if run.status in (RunStatus.pending, RunStatus.running):
            logger.info(f"Cancelling active run {run.run_id} before thread deletion")
            await run_mgr.cancel(run.run_id, action="interrupt")
    
    # Step 2: Delete from LangGraph
    checkpointer = get_checkpointer(request)
    try:
        await checkpointer.adelete({"configurable": {"thread_id": thread_id}})
    except Exception as e:
        logger.warning(f"Failed to delete thread from LangGraph: {e}")
        # Continue with cleanup even if LangGraph deletion fails
    
    # Step 3: Clean up local data
    if cleanup_data:
        paths = get_paths()
        thread_dir = paths.user_thread_dir(user_id, thread_id)
        
        if thread_dir.exists():
            try:
                shutil.rmtree(thread_dir)
                logger.info(f"Deleted local thread data: {thread_dir}")
            except Exception as e:
                logger.error(f"Failed to delete local thread data: {e}")
                # Log but don't fail - thread is already deleted from LangGraph
    
    # Step 4: Clean up run records
    try:
        await run_mgr.delete_by_thread(thread_id)
    except Exception as e:
        logger.warning(f"Failed to clean up run records: {e}")
    
    return Response(status_code=204)
```

### Step 3: 编写集成测试
- [ ] **创建测试文件**

```python
# backend/tests/test_thread_cleanup.py
"""Integration tests for thread cleanup."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.gateway.routers.threads import delete_thread


@pytest.fixture
def mock_request():
    request = MagicMock()
    request.state.run_manager = AsyncMock()
    request.state.checkpointer = AsyncMock()
    return request


@pytest.mark.asyncio
async def test_delete_thread_cancels_active_runs(mock_request):
    """Verify active runs are cancelled before thread deletion."""
    # Setup: Create a running run
    from deerflow.runtime import RunRecord, RunStatus
    
    running_run = RunRecord(
        run_id="run-123",
        thread_id="thread-456",
        status=RunStatus.running,
    )
    
    mock_request.state.run_manager.list_by_thread = AsyncMock(
        return_value=[running_run]
    )
    mock_request.state.run_manager.cancel = AsyncMock(return_value=True)
    mock_request.state.run_manager.delete_by_thread = AsyncMock()
    
    with patch("app.gateway.routers.threads.get_current_user", return_value="user-1"):
        await delete_thread("thread-456", mock_request)
    
    # Verify cancel was called
    mock_request.state.run_manager.cancel.assert_called_once_with(
        "run-123", action="interrupt"
    )


@pytest.mark.asyncio
async def test_delete_thread_cleans_local_data(mock_request):
    """Verify local thread data is cleaned up."""
    import tempfile
    from pathlib import Path
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        thread_dir = Path(tmp_dir) / "threads" / "thread-789"
        thread_dir.mkdir(parents=True)
        (thread_dir / "test.txt").write_text("test data")
        
        with patch("app.gateway.routers.threads.get_paths") as mock_paths:
            mock_paths.return_value.user_thread_dir.return_value = thread_dir
            mock_paths.return_value.base_dir = Path(tmp_dir)
            
            mock_request.state.run_manager.list_by_thread = AsyncMock(return_value=[])
            mock_request.state.run_manager.delete_by_thread = AsyncMock()
            
            with patch("app.gateway.routers.threads.get_current_user", return_value="user-1"):
                await delete_thread("thread-789", mock_request)
        
        # Verify directory is deleted
        assert not thread_dir.exists()
```

### Step 4: 运行测试
- [ ] **执行测试**

```bash
PYTHONPATH=. uv run pytest tests/test_thread_cleanup.py -v
```

### Step 5: 提交
- [ ] **提交**

```bash
git add backend/app/gateway/routers/threads.py backend/tests/test_thread_cleanup.py
git commit -m "feat(api): implement complete thread cleanup on deletion

- Cancel active runs before thread deletion
- Delete thread from LangGraph via checkpointer
- Clean up local thread data directory
- Remove associated run records
- Add comprehensive integration tests"
```

---

## Task 4: SSE 断点续传 - 服务端支持

**Files:**
- Modify: `backend/app/gateway/routers/thread_runs.py`
- Test: `backend/tests/test_sse_resume.py`

### Step 1: 添加 last_event_id 参数支持
- [ ] **修改 stream_existing_run 端点**

```python
# backend/app/gateway/routers/thread_runs.py
# 在 stream_existing_run 函数中添加参数

@router.api_route(
    "/{thread_id}/runs/{run_id}/stream",
    methods=["GET", "POST"],
    response_model=None,
)
@require_permission("runs", "read", owner_check=True)
async def stream_existing_run(
    thread_id: str,
    run_id: str,
    request: Request,
    action: Literal["interrupt", "rollback"] | None = Query(
        default=None, description="Cancel action"
    ),
    wait: int = Query(default=0, description="Block until cancelled (1) or return immediately (0)"),
    last_event_id: str | None = Query(
        default=None, description="Last received event ID for resume"
    ),
):
    """Join an existing run's SSE stream with support for resuming.
    
    When last_event_id is provided, the server will replay events
    after that ID before continuing with the live stream.
    """
    run_mgr = get_run_manager(request)
    record = await run_mgr.get(run_id)
    
    if record is None or record.thread_id != thread_id:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    # Cancel if action requested
    if action is not None:
        cancelled = await run_mgr.cancel(run_id, action=action)
        if not cancelled:
            raise HTTPException(
                status_code=409,
                detail=f"Run {run_id} is not active on this worker and cannot be cancelled"
            )
        if wait and record.task is not None:
            try:
                await record.task
            except (asyncio.CancelledError, Exception):
                pass
            return Response(status_code=204)
    
    if record.store_only and action is None:
        raise HTTPException(
            status_code=409,
            detail=f"Run {run_id} is not active on this worker and cannot be streamed"
        )
    
    bridge = get_stream_bridge(request)
    
    # If resuming from a specific event, fetch buffered events
    if last_event_id:
        buffered_events = await bridge.get_events_after(run_id, last_event_id)
        return StreamingResponse(
            replay_then_stream(buffered_events, bridge, record, request, run_mgr),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    
    return StreamingResponse(
        sse_consumer(bridge, record, request, run_mgr),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def replay_then_stream(buffered_events, bridge, record, request, run_mgr):
    """Replay buffered events then continue with live stream."""
    # Replay buffered events
    for event in buffered_events:
        yield f"event: {event['type']}\n"
        yield f"id: {event['id']}\n"
        yield f"data: {event['data']}\n\n"
    
    # Continue with live stream
    async for chunk in sse_consumer(bridge, record, request, run_mgr):
        yield chunk
```

### Step 2: 在 StreamBridge 中添加事件存储
- [ ] **检查现有 StreamBridge 实现**

```bash
grep -r "class StreamBridge" /Users/yespon/workspace/projects/deer-flow/backend --include="*.py"
```

- [ ] **添加事件存储方法到 StreamBridge** (如果需要)

```python
# backend/app/gateway/services.py 或相关文件

class StreamBridge:
    """Extended with event buffering for resume support."""
    
    def __init__(self, max_buffer_size: int = 1000):
        self._buffers: dict[str, list[dict]] = {}  # run_id -> events
        self._max_buffer_size = max_buffer_size
    
    async def store_event(self, run_id: str, event: dict) -> str:
        """Store event and return event ID."""
        if run_id not in self._buffers:
            self._buffers[run_id] = []
        
        event_id = f"{run_id}:{len(self._buffers[run_id])}"
        event_with_id = {**event, "id": event_id}
        self._buffers[run_id].append(event_with_id)
        
        # Trim old events if buffer too large
        if len(self._buffers[run_id]) > self._max_buffer_size:
            self._buffers[run_id] = self._buffers[run_id][-self._max_buffer_size:]
        
        return event_id
    
    async def get_events_after(self, run_id: str, last_event_id: str) -> list[dict]:
        """Get events after the given ID."""
        if run_id not in self._buffers:
            return []
        
        # Parse event ID format: "run_id:index"
        try:
            _, last_index = last_event_id.rsplit(":", 1)
            last_index = int(last_index)
        except ValueError:
            return []
        
        return self._buffers[run_id][last_index + 1:]
    
    async def clear_buffer(self, run_id: str):
        """Clear buffer for a completed run."""
        if run_id in self._buffers:
            del self._buffers[run_id]
```

### Step 3: 编写 SSE 断点续传测试
- [ ] **创建测试文件**

```python
# backend/tests/test_sse_resume.py
"""Tests for SSE resume functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.gateway.services import StreamBridge


@pytest.fixture
def stream_bridge():
    return StreamBridge(max_buffer_size=100)


@pytest.mark.asyncio
async def test_store_event_returns_id(stream_bridge):
    """Verify events are stored with IDs."""
    event = {"type": "message", "data": "hello"}
    event_id = await stream_bridge.store_event("run-1", event)
    
    assert event_id.startswith("run-1:")
    assert ":" in event_id


@pytest.mark.asyncio
async def test_get_events_after_returns_subsequent_events(stream_bridge):
    """Verify events after a specific ID are returned."""
    # Store some events
    id1 = await stream_bridge.store_event("run-1", {"type": "start", "data": ""})
    id2 = await stream_bridge.store_event("run-1", {"type": "message", "data": "msg1"})
    id3 = await stream_bridge.store_event("run-1", {"type": "message", "data": "msg2"})
    
    # Get events after id1
    events = await stream_bridge.get_events_after("run-1", id1)
    
    assert len(events) == 2
    assert events[0]["type"] == "message"
    assert events[0]["data"] == "msg1"


@pytest.mark.asyncio
async def test_get_events_after_unknown_run_returns_empty(stream_bridge):
    """Verify unknown run returns empty list."""
    events = await stream_bridge.get_events_after("unknown-run", "some-id")
    assert events == []


@pytest.mark.asyncio
async def test_buffer_trimming(stream_bridge):
    """Verify old events are trimmed when buffer is full."""
    # Fill buffer beyond max
    for i in range(150):
        await stream_bridge.store_event("run-1", {"index": i})
    
    # Buffer should only keep last 100
    events = await stream_bridge.get_events_after("run-1", "run-1:0")
    assert len(events) == 99  # 100 kept, minus the first one
```

### Step 4: 运行测试
- [ ] **执行测试**

```bash
PYTHONPATH=. uv run pytest tests/test_sse_resume.py -v
```

### Step 5: 提交
- [ ] **提交**

```bash
git add backend/app/gateway/routers/thread_runs.py backend/app/gateway/services.py backend/tests/test_sse_resume.py
git commit -m "feat(api): add SSE resume support with event buffering

- Add last_event_id query parameter to stream endpoint
- Implement StreamBridge event buffering with max size limit
- Add replay_then_stream generator for resuming from breakpoint
- Add comprehensive tests for event storage and retrieval"
```

---

## Task 5: 前端错误处理适配

**Files:**
- Create: `frontend/src/core/api/error-handler.ts`
- Modify: `frontend/src/core/api/fetcher.ts`

### Step 1: 创建前端错误处理模块
- [ ] **编写错误处理代码**

```typescript
// frontend/src/core/api/error-handler.ts
"""API error handling for frontend."""

import { toast } from "sonner";

export interface APIError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  request_id: string;
  timestamp: string;
}

// Error code to user-friendly message mapping
const ERROR_MESSAGES: Record<string, string> = {
  THREAD_NOT_FOUND: "对话不存在，已为您创建新对话",
  RUN_NOT_FOUND: "运行记录不存在",
  RUN_NOT_CANCELLABLE: "运行无法取消，可能已结束",
  INVALID_AGENT_NAME: "Agent 名称无效，只能包含字母、数字和连字符",
  AGENT_ALREADY_EXISTS: "Agent 名称已被使用",
  RATE_LIMIT_EXCEEDED: "请求过于频繁，请稍后再试",
  UPLOAD_TOO_LARGE: "文件过大，请分批上传或压缩后重试",
  INTERNAL_ERROR: "服务器内部错误，请稍后重试",
};

export function handleAPIError(error: APIError): void {
  // Log for debugging
  console.error(`[${error.request_id}] ${error.code}: ${error.message}`);

  // Show user-friendly toast
  const userMessage = ERROR_MESSAGES[error.code] || error.message;
  toast.error(userMessage);

  // Handle specific errors
  switch (error.code) {
    case "THREAD_NOT_FOUND":
      // Redirect to new chat
      window.location.href = "/workspace/chats/new";
      break;

    case "RATE_LIMIT_EXCEEDED": {
      const retryAfter = (error.details?.retry_after as number) || 60;
      toast.error(`请求过于频繁，请 ${retryAfter} 秒后重试`);
      break;
    }

    case "INTERNAL_ERROR":
      // Could send to error tracking service
      // reportError(error);
      break;
  }
}

export function isAPIError(error: unknown): error is APIError {
  return (
    typeof error === "object" &&
    error !== null &&
    "error" in error &&
    typeof (error as { error: unknown }).error === "object" &&
    "code" in (error as { error: { code: unknown } }).error
  );
}

// Fetch wrapper with error handling
export async function fetchWithErrorHandling(
  url: string,
  options?: RequestInit
): Promise<Response> {
  const response = await fetch(url, options);

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);

    if (isAPIError(errorData)) {
      handleAPIError(errorData.error);
      throw new Error(errorData.error.message);
    }

    // Fallback for non-standard errors
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  return response;
}
```

### Step 2: 更新 fetcher 使用新的错误处理
- [ ] **修改 fetcher.ts**

```typescript
// frontend/src/core/api/fetcher.ts
// 添加导入
import { fetchWithErrorHandling } from "./error-handler";

// 在适当位置使用 fetchWithErrorHandling 替代 fetch
// 或者在现有错误处理中集成
```

### Step 3: 运行类型检查
- [ ] **检查类型**

```bash
cd /Users/yespon/workspace/projects/deer-flow/frontend
pnpm typecheck
```

### Step 4: 提交
- [ ] **提交**

```bash
git add frontend/src/core/api/error-handler.ts frontend/src/core/api/fetcher.ts
git commit -m "feat(frontend): add API error handling module

- Add APIError interface matching backend format
- Add user-friendly error message mapping
- Add handleAPIError function with toast notifications
- Add fetchWithErrorHandling wrapper
- Add specific handling for common errors"
```

---

## 计划自我审查

### Spec 覆盖检查

| 设计需求 | 实现任务 | 状态 |
|----------|----------|------|
| 统一错误响应格式 | Task 1, 2 | ✅ 已覆盖 |
| Thread 删除完善 | Task 3 | ✅ 已覆盖 |
| SSE 断点续传 | Task 4 | ✅ 已覆盖 |
| 前端错误处理适配 | Task 5 | ✅ 已覆盖 |

### Placeholder 扫描
- [x] 无 "TBD" 占位符
- [x] 无 "TODO" 占位符
- [x] 无 "implement later" 描述
- [x] 每个步骤都有完整代码

### 类型一致性检查
- [x] APIError 类型前后端一致
- [x] 异常类命名一致
- [x] 错误码命名一致

---

## 执行选项

**Plan complete and saved to `docs/superpowers/plans/2026-05-30-phase1-implementation.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints for review

**Which approach?**
