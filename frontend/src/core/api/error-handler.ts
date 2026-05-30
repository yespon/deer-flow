/** API error handling for frontend. */

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
  const userMessage = ERROR_MESSAGES[error.code] ?? error.message;
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

export interface APIErrorResponse {
  error: APIError;
}

export function isAPIError(error: unknown): error is APIErrorResponse {
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
  options?: RequestInit,
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
