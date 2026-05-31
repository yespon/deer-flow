/** API error handling for frontend. */

import { toast } from "sonner";

/** Standardized API error structure returned by the backend. */
export interface APIError {
  /** Error code identifier (e.g., "RATE_LIMIT_EXCEEDED") */
  code: string;
  /** Human-readable error message */
  message: string;
  /** Additional error details, varies by error type */
  details?: Record<string, unknown>;
  /** Unique request ID for debugging */
  request_id: string;
  /** ISO timestamp when the error occurred */
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

/**
 * Handle API errors with user-friendly toast notifications and specific actions.
 * @param error - The API error to handle
 */
export function handleAPIError(error: APIError): void {
  // Log for debugging
  console.error(`[${error.request_id}] ${error.code}: ${error.message}`);

  // Handle specific errors
  switch (error.code) {
    case "THREAD_NOT_FOUND": {
      // Show user-friendly toast
      toast.error(ERROR_MESSAGES[error.code] ?? error.message);

      // Prevent infinite redirect loop
      const currentPath = window.location.pathname;
      const targetPath = "/workspace/chats/new";

      // Skip redirect if already on target path or recently redirected
      if (currentPath === targetPath) {
        console.debug(
          "[error-handler] Already on new chat page, skipping redirect",
        );
        break;
      }

      // Check if we recently redirected (prevent rapid-fire redirects)
      const lastRedirect = sessionStorage.getItem("thread_not_found_redirect");
      const now = Date.now();
      if (lastRedirect && now - parseInt(lastRedirect, 10) < 5000) {
        console.debug("[error-handler] Recent redirect detected, skipping");
        break;
      }

      // Record redirect timestamp and navigate
      sessionStorage.setItem("thread_not_found_redirect", now.toString());
      window.location.href = targetPath;
      break;
    }

    case "RATE_LIMIT_EXCEEDED": {
      const retryAfter =
        typeof error.details?.retry_after === "number"
          ? error.details.retry_after
          : 60;
      toast.error(`请求过于频繁，请 ${retryAfter} 秒后重试`);
      break;
    }

    case "INTERNAL_ERROR":
      // Could send to error tracking service
      // reportError(error);
      // Show user-friendly toast
      toast.error(ERROR_MESSAGES[error.code] ?? error.message);
      break;

    default:
      // Show user-friendly toast for other errors
      toast.error(ERROR_MESSAGES[error.code] ?? error.message);
      break;
  }
}

/** Wrapper for API error responses. */
export interface APIErrorResponse {
  /** The API error details */
  error: APIError;
}

/**
 * Check if an unknown value is an APIErrorResponse.
 * @param error - The value to check
 * @returns True if the value is an APIErrorResponse
 */
export function isAPIError(error: unknown): error is APIErrorResponse {
  return (
    typeof error === "object" &&
    error !== null &&
    "error" in error &&
    typeof (error as { error: unknown }).error === "object" &&
    "code" in (error as { error: { code: unknown } }).error
  );
}
