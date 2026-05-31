/**
 * Hook for resilient thread streaming using ResilientEventSource.
 *
 * This hook provides automatic reconnection with exponential backoff
 * for thread streaming scenarios. It's designed as an alternative to
 * the SDK's useStream when you need:
 * - Automatic reconnection with backoff
 * - Breakpoint resume via last_event_id
 * - Fine-grained control over reconnection behavior
 *
 * For most use cases, the SDK's useStream with reconnectOnMount is sufficient.
 * Use this hook when you need resilient streaming for custom endpoints.
 *
 * @example
 * ```typescript
 * const stream = useResilientThreadStream({
 *   threadId: "thread-123",
 *   onMessage: (event) => {
 *     const data = JSON.parse(event.data);
 *     console.log("Received:", data);
 *   },
 *   onError: (error) => {
 *     console.error("Stream failed:", error);
 *   },
 * });
 *
 * // Start streaming
 * stream.connect();
 *
 * // Cleanup on unmount
 * useEffect(() => {
 *   return () => stream.disconnect();
 * }, []);
 * ```
 */

import { useCallback, useEffect, useRef, useState } from "react";

import {
  ResilientEventSource,
  type ResilientStreamOptions,
  type ResilientStreamState,
} from "@/core/api/resilient-stream";

import { getLangGraphBaseURL } from "../config";

export interface UseResilientThreadStreamOptions extends Omit<
  ResilientStreamOptions,
  "url" | "onMessage"
> {
  /** Thread ID to stream from */
  threadId: string;
  /** Optional run ID for resuming a specific run */
  runId?: string;
  /** Callback for SSE messages */
  onMessage?: (data: unknown) => void;
  /** Whether to auto-connect on mount */
  autoConnect?: boolean;
}

export interface UseResilientThreadStreamReturn {
  /** Current stream state */
  state: ResilientStreamState;
  /** Connect to the stream */
  connect: () => void;
  /** Disconnect from the stream */
  disconnect: () => void;
  /** Whether currently connected */
  isConnected: boolean;
  /** Last error if any */
  error: Error | null;
}

/**
 * Hook for resilient thread streaming with automatic reconnection.
 *
 * @param options - Configuration options
 * @returns Stream control methods and state
 */
export function useResilientThreadStream(
  options: UseResilientThreadStreamOptions,
): UseResilientThreadStreamReturn {
  const {
    threadId,
    runId,
    onMessage,
    autoConnect = false,
    ...resilientOptions
  } = options;

  const [state, setState] = useState<ResilientStreamState>({
    state: "closed",
    retryCount: 0,
    lastEventId: null,
    isReconnecting: false,
  });

  const [error, setError] = useState<Error | null>(null);
  const streamRef = useRef<ResilientEventSource | null>(null);

  // Build the stream URL
  const buildUrl = useCallback((): string => {
    const baseUrl = getLangGraphBaseURL();
    // Remove trailing slash from base URL
    const cleanBaseUrl = baseUrl.replace(/\/$/, "");

    if (runId) {
      // Resume a specific run
      return `${cleanBaseUrl}/threads/${threadId}/runs/${runId}/stream`;
    }
    // Start a new stream
    return `${cleanBaseUrl}/threads/${threadId}/runs/stream`;
  }, [threadId, runId]);

  // Connect to the stream
  const connect = useCallback((): void => {
    if (streamRef.current) {
      streamRef.current.disconnect();
    }

    setError(null);

    streamRef.current = new ResilientEventSource({
      url: buildUrl(),
      onMessage: (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage?.(data);
        } catch {
          // If not JSON, pass raw data
          onMessage?.(event.data);
        }
        // Update state on each message
        setState(streamRef.current?.getState() ?? state);
      },
      onOpen: () => {
        setState(streamRef.current?.getState() ?? state);
      },
      onError: (err) => {
        setError(err);
        setState(streamRef.current?.getState() ?? state);
      },
      ...resilientOptions,
    });

    streamRef.current.connect();
  }, [buildUrl, onMessage, resilientOptions, state]);

  // Disconnect from the stream
  const disconnect = useCallback((): void => {
    streamRef.current?.disconnect();
    streamRef.current = null;
  }, []);

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  // Update state periodically while connected
  useEffect(() => {
    if (state.state !== "open" && state.state !== "connecting") {
      return;
    }

    const interval = setInterval(() => {
      if (streamRef.current) {
        setState(streamRef.current.getState());
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [state.state]);

  return {
    state,
    connect,
    disconnect,
    isConnected: state.state === "open",
    error,
  };
}
