/**
 * Resilient SSE (Server-Sent Events) client with automatic reconnection.
 *
 * Features:
 * - Automatic reconnection with exponential backoff
 * - Breakpoint resume support via last_event_id
 * - Configurable max retries and backoff parameters
 * - Event buffering during reconnection
 */

import { toast } from "sonner";

const noop = (): void => undefined;

export interface ResilientStreamOptions {
  /** URL to connect to */
  url: string;
  /** Callback for SSE events */
  onMessage: (event: MessageEvent) => void;
  /** Callback for connection open */
  onOpen?: () => void;
  /** Callback for errors */
  onError?: (error: Error) => void;
  /** Maximum number of reconnection attempts (default: 5) */
  maxRetries?: number;
  /** Base delay for exponential backoff in ms (default: 1000) */
  baseDelay?: number;
  /** Maximum delay between retries in ms (default: 30000) */
  maxDelay?: number;
  /** Whether to enable breakpoint resume (default: true) */
  enableResume?: boolean;
  /** Initial last_event_id for resume */
  initialLastEventId?: string | null;
  /** Custom headers to send with the request */
  headers?: Record<string, string>;
}

export interface ResilientStreamState {
  /** Current connection state */
  state: "connecting" | "open" | "closed" | "error";
  /** Number of reconnection attempts made */
  retryCount: number;
  /** Last received event ID */
  lastEventId: string | null;
  /** Whether currently reconnecting */
  isReconnecting: boolean;
}

/**
 * Resilient SSE client with automatic reconnection support.
 *
 * This class wraps the native EventSource API and adds:
 * - Automatic reconnection with exponential backoff
 * - Breakpoint resume using Last-Event-ID header
 * - State tracking and error handling
 *
 * @example
 * ```typescript
 * const stream = new ResilientEventSource({
 *   url: "/api/threads/123/runs/stream",
 *   onMessage: (event) => console.log("Received:", event.data),
 *   maxRetries: 5,
 * });
 *
 * stream.connect();
 *
 * // Later...
 * stream.disconnect();
 * ```
 */
export class ResilientEventSource {
  private eventSource: EventSource | null = null;
  private options: Required<ResilientStreamOptions>;
  private state: ResilientStreamState;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private abortController: AbortController | null = null;

  constructor(options: ResilientStreamOptions) {
    this.options = {
      maxRetries: 5,
      baseDelay: 1000,
      maxDelay: 30000,
      enableResume: true,
      initialLastEventId: null,
      headers: {},
      onOpen: noop,
      onError: noop,
      ...options,
    };

    this.state = {
      state: "closed",
      retryCount: 0,
      lastEventId: options.initialLastEventId ?? null,
      isReconnecting: false,
    };
  }

  /**
   * Get current stream state.
   */
  getState(): ResilientStreamState {
    return { ...this.state };
  }

  /**
   * Connect to the SSE endpoint.
   */
  connect(): void {
    if (this.eventSource?.readyState === EventSource.OPEN) {
      console.debug("[ResilientEventSource] Already connected");
      return;
    }

    this.clearReconnectTimer();
    this.state.state = "connecting";

    try {
      // Build URL with last_event_id if resume is enabled
      let url = this.options.url;
      if (this.options.enableResume && this.state.lastEventId) {
        const separator = url.includes("?") ? "&" : "?";
        url = `${url}${separator}last_event_id=${encodeURIComponent(this.state.lastEventId)}`;
      }

      console.debug(
        `[ResilientEventSource] Connecting to ${url}${this.state.isReconnecting ? " (reconnect)" : ""}`,
      );

      this.eventSource = new EventSource(url);

      this.eventSource.onopen = () => {
        console.debug("[ResilientEventSource] Connection opened");
        this.state.state = "open";
        this.state.retryCount = 0;
        this.state.isReconnecting = false;
        this.options.onOpen();
      };

      this.eventSource.onmessage = (event) => {
        // Update last_event_id for potential resume
        if (event.lastEventId) {
          this.state.lastEventId = event.lastEventId;
        }
        this.options.onMessage(event);
      };

      this.eventSource.onerror = (error) => {
        console.error("[ResilientEventSource] Connection error:", error);
        this.handleError();
      };
    } catch (error) {
      console.error(
        "[ResilientEventSource] Failed to create connection:",
        error,
      );
      this.handleError();
    }
  }

  /**
   * Disconnect from the SSE endpoint.
   */
  disconnect(): void {
    console.debug("[ResilientEventSource] Disconnecting");

    this.clearReconnectTimer();

    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    this.abortController?.abort();
    this.abortController = null;

    this.state.state = "closed";
    this.state.isReconnecting = false;
  }

  /**
   * Handle connection error and attempt reconnection if appropriate.
   */
  private handleError(): void {
    this.eventSource?.close();
    this.eventSource = null;

    this.state.state = "error";

    // Check if we should retry
    if (this.state.retryCount >= this.options.maxRetries) {
      console.error(
        `[ResilientEventSource] Max retries (${this.options.maxRetries}) exceeded`,
      );
      this.state.state = "error";
      this.options.onError(
        new Error(`Connection failed after ${this.options.maxRetries} retries`),
      );
      toast.error("连接失败，请刷新页面重试");
      return;
    }

    // Calculate backoff delay with jitter
    const delay = this.calculateBackoff();
    this.state.retryCount++;
    this.state.isReconnecting = true;

    console.debug(
      `[ResilientEventSource] Reconnecting in ${delay}ms (attempt ${this.state.retryCount}/${this.options.maxRetries})`,
    );

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Calculate exponential backoff delay with jitter.
   */
  private calculateBackoff(): number {
    // Exponential: baseDelay * 2^retryCount
    const exponential =
      this.options.baseDelay * Math.pow(2, this.state.retryCount);

    // Add jitter (±25%) to prevent thundering herd
    const jitter = exponential * 0.25 * (Math.random() * 2 - 1);

    // Cap at maxDelay
    return Math.min(exponential + jitter, this.options.maxDelay);
  }

  /**
   * Clear any pending reconnect timer.
   */
  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}

/**
 * Create a resilient SSE stream with the given options.
 *
 * This is a convenience factory function that creates and connects
 * a ResilientEventSource instance.
 *
 * @example
 * ```typescript
 * const stream = createResilientStream({
 *   url: "/api/threads/123/runs/stream",
 *   onMessage: (event) => console.log(event.data),
 * });
 *
 * // Clean up when done
 * stream.disconnect();
 * ```
 */
export function createResilientStream(
  options: ResilientStreamOptions,
): ResilientEventSource {
  const stream = new ResilientEventSource(options);
  stream.connect();
  return stream;
}
