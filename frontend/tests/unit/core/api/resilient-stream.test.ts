/**
 * Tests for ResilientEventSource
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import {
  ResilientEventSource,
  createResilientStream,
} from "@/core/api/resilient-stream";

// Mock EventSource that fails to connect (for retry tests)
class FailingMockEventSource extends EventTarget {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;

  readyState = FailingMockEventSource.CONNECTING;
  url = "";

  onopen: ((this: EventSource, ev: Event) => void) | null = null;
  onmessage: ((this: EventSource, ev: MessageEvent) => void) | null = null;
  onerror: ((this: EventSource, ev: Event) => void) | null = null;

  constructor(url: string) {
    super();
    this.url = url;

    // Simulate connection failure after a short delay
    setTimeout(() => {
      this.readyState = FailingMockEventSource.CLOSED;
      if (this.onerror) {
        this.onerror(new Event("error"));
      }
    }, 10);
  }

  close() {
    this.readyState = FailingMockEventSource.CLOSED;
  }
}

// Default mock that succeeds
global.EventSource = class MockEventSource extends EventTarget {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;

  readyState = MockEventSource.CONNECTING;
  url = "";

  onopen: ((this: EventSource, ev: Event) => void) | null = null;
  onmessage: ((this: EventSource, ev: MessageEvent) => void) | null = null;
  onerror: ((this: EventSource, ev: Event) => void) | null = null;

  constructor(url: string) {
    super();
    this.url = url;

    // Simulate connection opening
    setTimeout(() => {
      this.readyState = MockEventSource.OPEN;
      if (this.onopen) {
        this.onopen(new Event("open"));
      }
    }, 10);
  }

  close() {
    this.readyState = MockEventSource.CLOSED;
  }
} as unknown as typeof EventSource;

describe("ResilientEventSource", () => {
  let stream: ResilientEventSource | null = null;

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    stream?.disconnect();
    stream = null;
    vi.useRealTimers();
  });

  describe("connection", () => {
    it("should connect to the given URL", () => {
      const onMessage = vi.fn();
      stream = new ResilientEventSource({
        url: "http://test.com/stream",
        onMessage,
      });

      stream.connect();

      expect(stream.getState().state).toBe("connecting");
    });

    it("should not reconnect if already connected", async () => {
      const onMessage = vi.fn();
      stream = new ResilientEventSource({
        url: "http://test.com/stream",
        onMessage,
      });

      stream.connect();
      await vi.advanceTimersByTimeAsync(20); // Wait for connection to open

      const consoleSpy = vi.spyOn(console, "debug").mockImplementation(vi.fn());
      stream.connect(); // Try to connect again

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining("Already connected"),
      );
      consoleSpy.mockRestore();
    });

    it("should call onOpen when connection opens", async () => {
      const onOpen = vi.fn();
      stream = new ResilientEventSource({
        url: "http://test.com/stream",
        onMessage: vi.fn(),
        onOpen,
      });

      stream.connect();

      // Fast-forward past the connection timeout
      await vi.advanceTimersByTimeAsync(20);

      expect(onOpen).toHaveBeenCalled();
      expect(stream.getState().state).toBe("open");
    });
  });

  describe("message handling", () => {
    it("should call onMessage when receiving events", async () => {
      const onMessage = vi.fn();
      stream = new ResilientEventSource({
        url: "http://test.com/stream",
        onMessage,
      });

      stream.connect();
      await vi.advanceTimersByTimeAsync(20);

      // Simulate receiving a message
      const es = stream.eventSource!;
      if (es.onmessage) {
        es.onmessage(
          new MessageEvent("message", {
            data: JSON.stringify({ type: "test", content: "hello" }),
          }),
        );
      }

      expect(onMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          data: JSON.stringify({ type: "test", content: "hello" }),
        }),
      );
    });

    it("should track last_event_id for resume", async () => {
      const onMessage = vi.fn();
      stream = new ResilientEventSource({
        url: "http://test.com/stream",
        onMessage,
      });

      stream.connect();
      await vi.advanceTimersByTimeAsync(20);

      // Simulate receiving a message with event ID
      const es = stream.eventSource!;
      if (es.onmessage) {
        es.onmessage(
          new MessageEvent("message", {
            data: "test data",
            lastEventId: "event-123",
          }),
        );
      }

      expect(stream.getState().lastEventId).toBe("event-123");
    });
  });

  describe("reconnection", () => {
    it("should reconnect on error", async () => {
      const onMessage = vi.fn();
      const onError = vi.fn();

      stream = new ResilientEventSource({
        url: "http://test.com/stream",
        onMessage,
        onError,
        baseDelay: 100,
        maxRetries: 3,
      });

      stream.connect();
      await vi.advanceTimersByTimeAsync(20);

      // Simulate error
      const es = stream.eventSource!;
      if (es.onerror) {
        es.onerror(new Event("error"));
      }

      expect(stream.getState().state).toBe("error");
      expect(stream.getState().isReconnecting).toBe(true);
      expect(stream.getState().retryCount).toBe(1);
    });

    it("should include last_event_id in reconnect URL", async () => {
      const onMessage = vi.fn();
      stream = new ResilientEventSource({
        url: "http://test.com/stream",
        onMessage,
        initialLastEventId: "event-456",
        baseDelay: 100,
      });

      stream.connect();
      await vi.advanceTimersByTimeAsync(20);

      // Simulate error to trigger reconnect
      const es = stream.eventSource!;
      if (es.onerror) {
        es.onerror(new Event("error"));
      }

      // Fast-forward past backoff
      await vi.advanceTimersByTimeAsync(200);

      // Check that the new connection includes last_event_id
      expect(stream.getState().lastEventId).toBe("event-456");
    });

    it("should stop retrying after max retries exceeded", async () => {
      const onError = vi.fn();

      // Temporarily replace with failing mock
      const OriginalEventSource = global.EventSource;
      global.EventSource =
        FailingMockEventSource as unknown as typeof EventSource;

      stream = new ResilientEventSource({
        url: "http://test.com/stream",
        onMessage: vi.fn(),
        onError,
        baseDelay: 10,
        maxRetries: 2,
      });

      stream.connect();

      // Wait for initial connection attempt to fail + 2 retries
      // Each attempt: 10ms (connection timeout) + backoff (10ms * 2^n with jitter)
      await vi.advanceTimersByTimeAsync(100);

      // Restore original mock
      global.EventSource = OriginalEventSource;

      // Should have retried maxRetries times and given up
      expect(stream.getState().retryCount).toBeGreaterThanOrEqual(2);
      expect(stream.getState().state).toBe("error");

      // Should have called onError with failure message
      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({
          message: expect.stringContaining("Connection failed"),
        }),
      );
    });
  });

  describe("disconnect", () => {
    it("should clear reconnect timer on disconnect", async () => {
      const onMessage = vi.fn();
      stream = new ResilientEventSource({
        url: "http://test.com/stream",
        onMessage,
        baseDelay: 1000,
      });

      stream.connect();
      await vi.advanceTimersByTimeAsync(20);

      // Trigger error to start reconnection
      const es = stream.eventSource!;
      if (es.onerror) {
        es.onerror(new Event("error"));
      }

      expect(stream.getState().isReconnecting).toBe(true);

      // Disconnect should clear the timer
      stream.disconnect();

      expect(stream.getState().state).toBe("closed");
      expect(stream.getState().isReconnecting).toBe(false);
    });

    it("should be safe to disconnect multiple times", () => {
      stream = new ResilientEventSource({
        url: "http://test.com/stream",
        onMessage: vi.fn(),
      });

      stream.connect();
      stream.disconnect();
      stream.disconnect(); // Should not throw

      expect(stream.getState().state).toBe("closed");
    });
  });

  describe("createResilientStream", () => {
    it("should create and connect a stream", async () => {
      const onOpen = vi.fn();
      const onMessage = vi.fn();

      stream = createResilientStream({
        url: "http://test.com/stream",
        onMessage,
        onOpen,
      });

      await vi.advanceTimersByTimeAsync(20);

      expect(onOpen).toHaveBeenCalled();
    });
  });
});
