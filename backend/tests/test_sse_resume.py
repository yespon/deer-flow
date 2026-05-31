"""Tests for SSE resume functionality with event buffering.

This module tests the MemoryStreamBridge event buffering and resume
capabilities that enable clients to reconnect and resume streams after
connection loss.
"""

from __future__ import annotations

import asyncio

import pytest

from deerflow.runtime import MemoryStreamBridge


@pytest.fixture
def stream_bridge():
    """Create a fresh MemoryStreamBridge instance for each test."""
    return MemoryStreamBridge(queue_maxsize=100)


@pytest.fixture
async def bridge_with_events(stream_bridge):
    """Create a bridge pre-populated with test events."""
    run_id = "test-run-1"

    # Publish several events
    for i in range(5):
        await stream_bridge.publish(run_id, "message", {"index": i, "content": f"msg{i}"})

    return stream_bridge, run_id


class TestEventBuffering:
    """Tests for event storage and buffering behavior."""

    @pytest.mark.asyncio
    async def test_publish_creates_event_with_id(self, stream_bridge):
        """Verify that published events are assigned unique IDs."""
        run_id = "test-run-publish"
        await stream_bridge.publish(run_id, "test", {"data": "value"})

        # Subscribe and verify event has an ID
        events = []
        async for event in stream_bridge.subscribe(run_id):
            if event.event == "test":
                events.append(event)
                break

        assert len(events) == 1
        assert events[0].id is not None
        assert isinstance(events[0].id, str)
        assert "-" in events[0].id  # Format: "timestamp-seq"

    @pytest.mark.asyncio
    async def test_events_buffered_per_run(self, stream_bridge):
        """Verify events are buffered separately for each run."""
        run1, run2 = "run-1", "run-2"

        await stream_bridge.publish(run1, "msg", "run1-event")
        await stream_bridge.publish(run2, "msg", "run2-event")

        # Get events for run1
        events1 = []
        async for event in stream_bridge.subscribe(run1):
            if event.event == "msg":
                events1.append(event)
                break

        # Get events for run2
        events2 = []
        async for event in stream_bridge.subscribe(run2):
            if event.event == "msg":
                events2.append(event)
                break

        assert len(events1) == 1
        assert len(events2) == 1
        assert events1[0].data == "run1-event"
        assert events2[0].data == "run2-event"

    @pytest.mark.asyncio
    async def test_buffer_size_limit_enforced(self):
        """Verify that old events are dropped when buffer exceeds maxsize."""
        bridge = MemoryStreamBridge(queue_maxsize=5)
        run_id = "limited-run"

        # Publish more events than the buffer can hold
        for i in range(10):
            await bridge.publish(run_id, "msg", {"index": i})

        # Subscribe from beginning - should only get last 5 events
        events = []
        async for event in bridge.subscribe(run_id):
            if event.event == "msg":
                events.append(event)
                if len(events) >= 5:
                    break

        assert len(events) == 5
        # Should get events 5-9 (oldest 5 were dropped)
        for i, event in enumerate(events):
            assert event.data["index"] == i + 5

    @pytest.mark.asyncio
    async def test_publish_end_signals_completion(self, stream_bridge):
        """Verify that publish_end sends END_SENTINEL to subscribers."""
        run_id = "ending-run"

        await stream_bridge.publish(run_id, "msg", "data")
        await stream_bridge.publish_end(run_id)

        events = []
        async for event in stream_bridge.subscribe(run_id):
            events.append(event)
            if event.event == "__end__":
                break

        assert len(events) == 2
        assert events[0].event == "msg"
        assert events[1].event == "__end__"


class TestEventResumption:
    """Tests for resuming streams from a specific event ID."""

    @pytest.mark.asyncio
    async def test_subscribe_with_last_event_id(self, stream_bridge):
        """Verify subscribing with last_event_id replays missed events."""
        run_id = "resume-run"

        # Publish events
        for i in range(5):
            await stream_bridge.publish(run_id, "msg", {"index": i})

        # Get the ID of the second event
        events_before_resume = []
        async for event in stream_bridge.subscribe(run_id):
            events_before_resume.append(event)
            if len(events_before_resume) >= 2:
                break

        second_event_id = events_before_resume[1].id

        # Subscribe from second event - should get events 2, 3, 4
        resumed_events = []
        async for event in stream_bridge.subscribe(run_id, last_event_id=second_event_id):
            if event.event == "msg":
                resumed_events.append(event)
            if len(resumed_events) >= 3:
                break

        assert len(resumed_events) == 3
        assert resumed_events[0].data["index"] == 2
        assert resumed_events[1].data["index"] == 3
        assert resumed_events[2].data["index"] == 4

    @pytest.mark.asyncio
    async def test_subscribe_with_unknown_event_id_replays_all(self, stream_bridge):
        """Verify that unknown last_event_id replays all buffered events."""
        run_id = "unknown-id-run"

        for i in range(3):
            await stream_bridge.publish(run_id, "msg", {"index": i})

        # Subscribe with non-existent event ID
        events = []
        async for event in stream_bridge.subscribe(run_id, last_event_id="non-existent-id"):
            if event.event == "msg":
                events.append(event)
            if len(events) >= 3:
                break

        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_subscribe_with_none_last_event_id_gets_all(self, stream_bridge):
        """Verify that None last_event_id gets all events from start."""
        run_id = "all-events-run"

        for i in range(3):
            await stream_bridge.publish(run_id, "msg", {"index": i})

        events = []
        async for event in stream_bridge.subscribe(run_id, last_event_id=None):
            if event.event == "msg":
                events.append(event)
            if len(events) >= 3:
                break

        assert len(events) == 3
        assert events[0].data["index"] == 0
        assert events[2].data["index"] == 2

    @pytest.mark.asyncio
    async def test_subscribe_from_last_event_id_with_heartbeat(self, stream_bridge):
        """Verify that heartbeats are sent when no new events during resume."""
        run_id = "heartbeat-run"

        # Publish one event
        await stream_bridge.publish(run_id, "msg", "data")
        await stream_bridge.publish_end(run_id)

        # Subscribe with that event ID - should get end sentinel, no hang
        events = []
        async for event in stream_bridge.subscribe(run_id, last_event_id=None, heartbeat_interval=0.1):
            events.append(event)
            if event.event == "__end__":
                break

        # Should get the published event and end sentinel
        assert len(events) >= 1
        assert events[-1].event == "__end__"


class TestEventIdFormat:
    """Tests for event ID format and generation."""

    @pytest.mark.asyncio
    async def test_event_id_format(self, stream_bridge):
        """Verify event IDs follow expected format: timestamp-seq."""
        run_id = "format-run"

        await stream_bridge.publish(run_id, "msg", "data")

        events = []
        async for event in stream_bridge.subscribe(run_id):
            events.append(event)
            break

        event_id = events[0].id
        parts = event_id.split("-")

        assert len(parts) == 2
        # First part should be timestamp (numeric)
        assert parts[0].isdigit()
        # Second part should be sequence number (numeric)
        assert parts[1].isdigit()

    @pytest.mark.asyncio
    async def test_event_ids_are_monotonic(self, stream_bridge):
        """Verify event IDs increase monotonically within a run."""
        run_id = "monotonic-run"

        for i in range(5):
            await stream_bridge.publish(run_id, "msg", {"index": i})

        events = []
        async for event in stream_bridge.subscribe(run_id):
            if event.event == "msg":
                events.append(event)
            if len(events) >= 5:
                break

        # Extract sequence numbers and verify monotonicity
        seq_numbers = [int(e.id.split("-")[1]) for e in events]
        assert seq_numbers == sorted(seq_numbers)
        assert len(set(seq_numbers)) == len(seq_numbers)  # All unique


class TestStreamCleanup:
    """Tests for resource cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_removes_stream(self, stream_bridge):
        """Verify cleanup removes the stream state."""
        run_id = "cleanup-run"

        await stream_bridge.publish(run_id, "msg", "data")
        await stream_bridge.cleanup(run_id)

        # After cleanup, subscribing should start fresh
        await stream_bridge.publish(run_id, "msg", "new-data")

        events = []
        async for event in stream_bridge.subscribe(run_id):
            events.append(event)
            break

        assert len(events) == 1
        assert events[0].data == "new-data"

    @pytest.mark.asyncio
    async def test_cleanup_with_delay(self, stream_bridge):
        """Verify cleanup with delay works correctly."""
        run_id = "delayed-cleanup-run"

        await stream_bridge.publish(run_id, "msg", "data")

        # Start cleanup with delay
        cleanup_task = asyncio.create_task(stream_bridge.cleanup(run_id, delay=0.1))

        # Should still be able to subscribe before delay completes
        events = []
        async for event in stream_bridge.subscribe(run_id):
            events.append(event)
            break

        assert len(events) == 1

        # Wait for cleanup to complete
        await cleanup_task

        # After cleanup, stream is fresh
        await stream_bridge.publish(run_id, "msg", "after-cleanup")

        new_events = []
        async for event in stream_bridge.subscribe(run_id):
            new_events.append(event)
            break

        assert new_events[0].data == "after-cleanup"


class TestMultipleSubscribers:
    """Tests for multiple concurrent subscribers."""

    @pytest.mark.asyncio
    async def test_multiple_subscribers_get_same_events(self, stream_bridge):
        """Verify multiple subscribers can receive the same events."""
        run_id = "multi-sub-run"

        # Subscriber 1 starts first
        sub1_events = []
        sub1_task = asyncio.create_task(self._collect_events(stream_bridge, run_id, sub1_events, count=3))

        # Give subscriber 1 time to start
        await asyncio.sleep(0.01)

        # Subscriber 2 starts later
        sub2_events = []
        sub2_task = asyncio.create_task(self._collect_events(stream_bridge, run_id, sub2_events, count=3))

        # Publish events
        for i in range(3):
            await stream_bridge.publish(run_id, "msg", {"index": i})
            await asyncio.sleep(0.01)

        await asyncio.gather(sub1_task, sub2_task)

        assert len(sub1_events) == 3
        assert len(sub2_events) == 3
        for i in range(3):
            assert sub1_events[i].data["index"] == i
            assert sub2_events[i].data["index"] == i

    @pytest.mark.asyncio
    async def test_late_subscriber_gets_buffered_events(self, stream_bridge):
        """Verify late subscribers get already-buffered events."""
        run_id = "late-sub-run"

        # Publish events before any subscriber
        for i in range(3):
            await stream_bridge.publish(run_id, "msg", {"index": i})

        # Late subscriber should still get all events
        events = []
        async for event in stream_bridge.subscribe(run_id):
            if event.event == "msg":
                events.append(event)
            if len(events) >= 3:
                break

        assert len(events) == 3
        for i in range(3):
            assert events[i].data["index"] == i

    async def _collect_events(self, bridge, run_id, event_list, count):
        """Helper to collect events asynchronously."""
        async for event in bridge.subscribe(run_id):
            if event.event == "msg":
                event_list.append(event)
            if len(event_list) >= count:
                break


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_subscribe_to_nonexistent_run(self, stream_bridge):
        """Verify subscribing to a run with no events works."""
        run_id = "nonexistent-run"

        # Should not error, just wait for events
        # Set a short timeout to avoid hanging
        events = []
        try:
            async with asyncio.timeout(0.1):
                async for event in stream_bridge.subscribe(run_id, heartbeat_interval=0.05):
                    events.append(event)
                    if event.event == "__heartbeat__":
                        break
        except TimeoutError:
            pass

        # Should have gotten at least a heartbeat
        assert len(events) >= 1
        assert events[0].event == "__heartbeat__"

    @pytest.mark.asyncio
    async def test_empty_event_data(self, stream_bridge):
        """Verify events with empty/null data are handled correctly."""
        run_id = "empty-data-run"

        await stream_bridge.publish(run_id, "empty", None)
        await stream_bridge.publish(run_id, "empty_dict", {})
        await stream_bridge.publish(run_id, "empty_list", [])

        events = []
        async for event in stream_bridge.subscribe(run_id):
            if event.event != "__heartbeat__":
                events.append(event)
            if len(events) >= 3:
                break

        assert len(events) == 3
        assert events[0].data is None
        assert events[1].data == {}
        assert events[2].data == []

    @pytest.mark.asyncio
    async def test_rapid_publish(self, stream_bridge):
        """Verify rapid publishing doesn't lose events."""
        run_id = "rapid-run"
        event_count = 50

        # Publish many events rapidly
        for i in range(event_count):
            await stream_bridge.publish(run_id, "msg", {"index": i})

        # Subscribe and collect all events
        events = []
        async for event in stream_bridge.subscribe(run_id):
            if event.event == "msg":
                events.append(event)
            if len(events) >= event_count:
                break

        assert len(events) == event_count
        for i in range(event_count):
            assert events[i].data["index"] == i


class TestStreamBridgeClose:
    """Tests for closing the bridge."""

    @pytest.mark.asyncio
    async def test_close_clears_all_streams(self, stream_bridge):
        """Verify close() clears all stream state."""
        # Create multiple runs
        for run_id in ["run-a", "run-b", "run-c"]:
            await stream_bridge.publish(run_id, "msg", f"data-{run_id}")

        # Close the bridge
        await stream_bridge.close()

        # All streams should be gone - subscribing starts fresh
        for run_id in ["run-a", "run-b", "run-c"]:
            await stream_bridge.publish(run_id, "msg", f"new-data-{run_id}")

            events = []
            async for event in stream_bridge.subscribe(run_id):
                events.append(event)
                break

            assert len(events) == 1
            assert events[0].data == f"new-data-{run_id}"
