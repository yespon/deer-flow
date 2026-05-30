"""Unified API error handling.

This module provides a centralized exception handling system for the Gateway API.

Error Response Schema:
    All API errors follow a consistent JSON structure:

    {
        "error": {
            "code": "ERROR_CODE",        // Machine-readable error identifier
            "message": "Human readable description",
            "details": {...},              // Optional error-specific data
            "request_id": "uuid-prefix",   // For request tracing (8 chars)
            "timestamp": "ISO-8601 UTC"    // When the error occurred
        }
    }

Base Class:
    APIError: Base exception class that all API errors inherit from.
    Provides consistent attributes: code, message, status_code, details.

Usage:
    Raise specific error types in route handlers:
        raise ThreadNotFoundError("thread-123")

    The exception handlers (api_error_handler, generic_exception_handler)
    automatically convert exceptions to the standard JSON response format.
"""

import time
import uuid
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class APIError(Exception):
    """Base API error with structured response."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
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


def _build_error_response(
    code: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    """Build a standardized error response.

    Args:
        code: Machine-readable error code
        message: Human-readable error message
        status_code: HTTP status code
        details: Optional error-specific details

    Returns:
        JSONResponse with standardized error structure
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
                "request_id": str(uuid.uuid4())[:8],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        },
    )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Global API error handler."""
    return _build_error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unexpected exceptions."""
    return _build_error_response(
        code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        status_code=500,
        details={},
    )
