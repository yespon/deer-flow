"""Integration tests for thread cleanup."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def mock_request():
    """Create a mock request with required state objects."""
    request = MagicMock()
    request.state.run_manager = AsyncMock()
    request.state.checkpointer = AsyncMock()
    request.app.state.checkpointer = AsyncMock()
    # Add test bypass auth flag for the authz decorator
    request._deerflow_test_bypass_auth = True
    request.cookies = {}
    return request


@pytest.mark.asyncio
async def test_delete_thread_cancels_active_runs(mock_request):
    """Verify active runs are cancelled before thread deletion."""
    from app.gateway.routers.threads import delete_thread_data
    from deerflow.runtime import RunRecord, RunStatus

    # Setup: Create a running run
    running_run = RunRecord(
        run_id="run-123",
        thread_id="thread-456",
        assistant_id=None,
        status=RunStatus.running,
        on_disconnect="cancel",
    )

    mock_request.state.run_manager.list_by_thread = AsyncMock(return_value=[running_run])
    mock_request.state.run_manager.cancel = AsyncMock(return_value=True)
    mock_request.state.run_manager.delete_by_thread = AsyncMock(return_value=1)

    # Mock checkpointer
    mock_request.app.state.checkpointer = AsyncMock()

    with patch("app.gateway.routers.threads.get_current_user", return_value="user-1"):
        with patch("app.gateway.routers.threads.get_run_manager", return_value=mock_request.state.run_manager):
            with patch("app.gateway.routers.threads.get_checkpointer", return_value=mock_request.app.state.checkpointer):
                with patch("app.gateway.deps.get_thread_store", return_value=AsyncMock()):
                    await delete_thread_data("thread-456", request=mock_request)

    # Verify cancel was called for the active run
    mock_request.state.run_manager.cancel.assert_called_once_with("run-123", action="interrupt")


@pytest.mark.asyncio
async def test_delete_thread_cancels_pending_runs(mock_request):
    """Verify pending runs are also cancelled before thread deletion."""
    from app.gateway.routers.threads import delete_thread_data
    from deerflow.runtime import RunRecord, RunStatus

    # Setup: Create a pending run
    pending_run = RunRecord(
        run_id="run-pending",
        thread_id="thread-789",
        assistant_id=None,
        status=RunStatus.pending,
        on_disconnect="cancel",
    )

    mock_request.state.run_manager.list_by_thread = AsyncMock(return_value=[pending_run])
    mock_request.state.run_manager.cancel = AsyncMock(return_value=True)
    mock_request.state.run_manager.delete_by_thread = AsyncMock(return_value=1)

    # Mock checkpointer
    mock_request.app.state.checkpointer = AsyncMock()

    with patch("app.gateway.routers.threads.get_current_user", return_value="user-1"):
        with patch("app.gateway.routers.threads.get_run_manager", return_value=mock_request.state.run_manager):
            with patch("app.gateway.routers.threads.get_checkpointer", return_value=mock_request.app.state.checkpointer):
                with patch("app.gateway.deps.get_thread_store", return_value=AsyncMock()):
                    await delete_thread_data("thread-789", request=mock_request)

    # Verify cancel was called for the pending run
    mock_request.state.run_manager.cancel.assert_called_once_with("run-pending", action="interrupt")


@pytest.mark.asyncio
async def test_delete_thread_skips_completed_runs(mock_request):
    """Verify completed runs are not cancelled."""
    from app.gateway.routers.threads import delete_thread_data
    from deerflow.runtime import RunRecord, RunStatus

    # Setup: Create completed and error runs
    completed_run = RunRecord(
        run_id="run-done",
        thread_id="thread-done",
        assistant_id=None,
        status=RunStatus.success,
        on_disconnect="cancel",
    )
    error_run = RunRecord(
        run_id="run-error",
        thread_id="thread-done",
        assistant_id=None,
        status=RunStatus.error,
        on_disconnect="cancel",
    )

    mock_request.state.run_manager.list_by_thread = AsyncMock(return_value=[completed_run, error_run])
    mock_request.state.run_manager.cancel = AsyncMock(return_value=True)
    mock_request.state.run_manager.delete_by_thread = AsyncMock(return_value=2)

    # Mock checkpointer
    mock_request.app.state.checkpointer = AsyncMock()

    with patch("app.gateway.routers.threads.get_current_user", return_value="user-1"):
        with patch("app.gateway.routers.threads.get_run_manager", return_value=mock_request.state.run_manager):
            with patch("app.gateway.routers.threads.get_checkpointer", return_value=mock_request.app.state.checkpointer):
                with patch("app.gateway.deps.get_thread_store", return_value=AsyncMock()):
                    await delete_thread_data("thread-done", request=mock_request)

    # Verify cancel was NOT called for completed/error runs
    mock_request.state.run_manager.cancel.assert_not_called()


@pytest.mark.asyncio
async def test_delete_thread_cleans_run_records(mock_request):
    """Verify run records are cleaned up."""
    from app.gateway.routers.threads import delete_thread_data

    mock_request.state.run_manager.list_by_thread = AsyncMock(return_value=[])
    mock_request.state.run_manager.delete_by_thread = AsyncMock(return_value=3)

    # Mock checkpointer
    mock_request.app.state.checkpointer = AsyncMock()

    with patch("app.gateway.routers.threads.get_current_user", return_value="user-1"):
        with patch("app.gateway.routers.threads.get_run_manager", return_value=mock_request.state.run_manager):
            with patch("app.gateway.routers.threads.get_checkpointer", return_value=mock_request.app.state.checkpointer):
                with patch("app.gateway.deps.get_thread_store", return_value=AsyncMock()):
                    await delete_thread_data("thread-abc", request=mock_request)

    # Verify delete_by_thread was called
    mock_request.state.run_manager.delete_by_thread.assert_called_once_with("thread-abc", user_id="user-1")


@pytest.mark.asyncio
async def test_delete_thread_deletes_from_checkpointer(mock_request):
    """Verify thread is deleted from checkpointer."""
    from app.gateway.routers.threads import delete_thread_data

    mock_request.state.run_manager.list_by_thread = AsyncMock(return_value=[])
    mock_request.state.run_manager.delete_by_thread = AsyncMock(return_value=0)

    # Mock checkpointer with adelete_thread method
    mock_checkpointer = AsyncMock()
    mock_checkpointer.adelete_thread = AsyncMock()

    with patch("app.gateway.routers.threads.get_current_user", return_value="user-1"):
        with patch("app.gateway.routers.threads.get_run_manager", return_value=mock_request.state.run_manager):
            with patch("app.gateway.routers.threads.get_checkpointer", return_value=mock_checkpointer):
                with patch("app.gateway.deps.get_thread_store", return_value=AsyncMock()):
                    await delete_thread_data("thread-check", request=mock_request)

    # Verify checkpointer.adelete_thread was called
    mock_checkpointer.adelete_thread.assert_called_once_with("thread-check")


@pytest.mark.asyncio
async def test_delete_thread_deletes_from_checkpointer_fallback(mock_request):
    """Verify thread is deleted from checkpointer using fallback adelete method."""
    from app.gateway.routers.threads import delete_thread_data

    mock_request.state.run_manager.list_by_thread = AsyncMock(return_value=[])
    mock_request.state.run_manager.delete_by_thread = AsyncMock(return_value=0)

    # Mock checkpointer without adelete_thread method (uses fallback)
    # Create a simple object that doesn't have adelete_thread
    mock_checkpointer = MagicMock()
    mock_checkpointer.adelete = AsyncMock()
    # Ensure adelete_thread doesn't exist
    if hasattr(mock_checkpointer, "adelete_thread"):
        delattr(mock_checkpointer, "adelete_thread")

    with patch("app.gateway.routers.threads.get_current_user", return_value="user-1"):
        with patch("app.gateway.routers.threads.get_run_manager", return_value=mock_request.state.run_manager):
            with patch("app.gateway.routers.threads.get_checkpointer", return_value=mock_checkpointer):
                with patch("app.gateway.deps.get_thread_store", return_value=AsyncMock()):
                    await delete_thread_data("thread-fallback", request=mock_request)

    # Verify checkpointer.adelete was called with correct config
    mock_checkpointer.adelete.assert_called_once_with({"configurable": {"thread_id": "thread-fallback"}})


@pytest.mark.asyncio
async def test_delete_thread_handles_checkpointer_errors(mock_request):
    """Verify thread deletion continues even if checkpointer fails."""
    from app.gateway.routers.threads import delete_thread_data

    mock_request.state.run_manager.list_by_thread = AsyncMock(return_value=[])
    mock_request.state.run_manager.delete_by_thread = AsyncMock(return_value=0)

    # Mock checkpointer that raises exception
    mock_checkpointer = AsyncMock()
    mock_checkpointer.adelete_thread = AsyncMock(side_effect=Exception("Checkpointer error"))

    with patch("app.gateway.routers.threads.get_current_user", return_value="user-1"):
        with patch("app.gateway.routers.threads.get_run_manager", return_value=mock_request.state.run_manager):
            with patch("app.gateway.routers.threads.get_checkpointer", return_value=mock_checkpointer):
                with patch("app.gateway.deps.get_thread_store", return_value=AsyncMock()):
                    # Should not raise exception
                    response = await delete_thread_data("thread-error", request=mock_request)

    # Verify response is still returned successfully
    assert response.success is True


@pytest.mark.asyncio
async def test_delete_thread_handles_run_cleanup_errors(mock_request):
    """Verify thread deletion continues even if run cleanup fails."""
    from app.gateway.routers.threads import delete_thread_data

    mock_request.state.run_manager.list_by_thread = AsyncMock(return_value=[])
    mock_request.state.run_manager.delete_by_thread = AsyncMock(side_effect=Exception("Delete runs error"))

    # Mock checkpointer
    mock_checkpointer = AsyncMock()

    with patch("app.gateway.routers.threads.get_current_user", return_value="user-1"):
        with patch("app.gateway.routers.threads.get_run_manager", return_value=mock_request.state.run_manager):
            with patch("app.gateway.routers.threads.get_checkpointer", return_value=mock_checkpointer):
                with patch("app.gateway.deps.get_thread_store", return_value=AsyncMock()):
                    # Should not raise exception
                    response = await delete_thread_data("thread-run-error", request=mock_request)

    # Verify response is still returned successfully
    assert response.success is True


@pytest.mark.asyncio
async def test_run_manager_delete_by_thread_with_memory_store():
    """Test RunManager.delete_by_thread with MemoryRunStore."""
    from deerflow.runtime import RunManager
    from deerflow.runtime.runs.store.memory import MemoryRunStore

    store = MemoryRunStore()
    manager = RunManager(store=store)

    # Create some runs for thread-1
    await manager.create("thread-1", on_disconnect="cancel")
    await manager.create("thread-1", on_disconnect="cancel")

    # Create a run for a different thread
    await manager.create("thread-2", on_disconnect="cancel")

    # Verify runs exist
    assert len(await manager.list_by_thread("thread-1")) == 2
    assert len(await manager.list_by_thread("thread-2")) == 1

    # Delete runs for thread-1
    deleted = await manager.delete_by_thread("thread-1")

    # Verify only thread-1 runs were deleted
    assert deleted == 2
    assert len(await manager.list_by_thread("thread-1")) == 0
    assert len(await manager.list_by_thread("thread-2")) == 1


@pytest.mark.asyncio
async def test_run_manager_delete_by_thread_without_store():
    """Test RunManager.delete_by_thread without backing store."""
    from deerflow.runtime import RunManager

    # No backing store
    manager = RunManager(store=None)

    # Create some runs for thread-1
    await manager.create("thread-1", on_disconnect="cancel")
    await manager.create("thread-1", on_disconnect="cancel")

    # Create a run for a different thread
    await manager.create("thread-2", on_disconnect="cancel")

    # Delete runs for thread-1
    deleted = await manager.delete_by_thread("thread-1")

    # Verify only thread-1 runs were deleted from memory
    assert deleted == 2
    assert len(await manager.list_by_thread("thread-1")) == 0
    assert len(await manager.list_by_thread("thread-2")) == 1


@pytest.mark.asyncio
async def test_memory_run_store_delete_by_thread():
    """Test MemoryRunStore.delete_by_thread."""
    from deerflow.runtime.runs.store.memory import MemoryRunStore

    store = MemoryRunStore()

    # Add runs for different threads
    await store.put("run-1", thread_id="thread-a", status="completed")
    await store.put("run-2", thread_id="thread-a", status="completed")
    await store.put("run-3", thread_id="thread-b", status="completed")

    # Delete runs for thread-a
    deleted = await store.delete_by_thread("thread-a")

    assert deleted == 2
    assert await store.get("run-1") is None
    assert await store.get("run-2") is None
    assert await store.get("run-3") is not None
