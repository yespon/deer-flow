"""Tests for API exception handling."""

import asyncio
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.exceptions import (
    AgentAlreadyExistsError,
    APIError,
    InvalidAgentNameError,
    RateLimitExceededError,
    RunNotCancellableError,
    RunNotFoundError,
    ThreadNotFoundError,
    api_error_handler,
    generic_exception_handler,
)


@pytest.fixture
def app():
    app = FastAPI()
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    @app.get("/test/thread-not-found")
    async def test_thread_not_found():
        raise ThreadNotFoundError("thread-123")

    @app.get("/test/run-not-found")
    async def test_run_not_found():
        raise RunNotFoundError("run-456")

    @app.get("/test/rate-limit")
    async def test_rate_limit():
        raise RateLimitExceededError(retry_after=30)

    @app.get("/test/run-not-cancellable")
    async def test_run_not_cancellable():
        raise RunNotCancellableError("run-789", "completed")

    @app.get("/test/invalid-agent-name")
    async def test_invalid_agent_name():
        raise InvalidAgentNameError("invalid@name")

    @app.get("/test/agent-already-exists")
    async def test_agent_already_exists():
        raise AgentAlreadyExistsError("my-agent")

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_api_error_base_class():
    """Test that APIError base class has correct default attributes."""
    exc = APIError(code="TEST_ERROR", message="Test message")
    assert exc.code == "TEST_ERROR"
    assert exc.message == "Test message"
    assert exc.status_code == 500
    assert exc.details == {}


def test_api_error_with_custom_status_and_details():
    """Test APIError with custom status code and details."""
    exc = APIError(
        code="CUSTOM_ERROR",
        message="Custom message",
        status_code=400,
        details={"field": "value"},
    )
    assert exc.code == "CUSTOM_ERROR"
    assert exc.message == "Custom message"
    assert exc.status_code == 400
    assert exc.details == {"field": "value"}


def test_thread_not_found_error(client):
    response = client.get("/test/thread-not-found")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "THREAD_NOT_FOUND"
    assert "thread-123" in data["error"]["message"]
    assert data["error"]["details"]["thread_id"] == "thread-123"
    assert "suggestion" in data["error"]["details"]
    assert "request_id" in data["error"]
    assert "timestamp" in data["error"]


def test_run_not_found_error(client):
    response = client.get("/test/run-not-found")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "RUN_NOT_FOUND"
    assert "run-456" in data["error"]["message"]
    assert data["error"]["details"]["run_id"] == "run-456"
    assert "request_id" in data["error"]
    assert "timestamp" in data["error"]


def test_rate_limit_error(client):
    response = client.get("/test/rate-limit")
    assert response.status_code == 429
    data = response.json()
    assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert data["error"]["details"]["retry_after"] == 30
    assert "request_id" in data["error"]
    assert "timestamp" in data["error"]


def test_run_not_cancellable_error(client):
    response = client.get("/test/run-not-cancellable")
    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "RUN_NOT_CANCELLABLE"
    assert "run-789" in data["error"]["message"]
    assert "completed" in data["error"]["message"]
    assert data["error"]["details"]["run_id"] == "run-789"
    assert data["error"]["details"]["status"] == "completed"
    assert "request_id" in data["error"]
    assert "timestamp" in data["error"]


def test_invalid_agent_name_error(client):
    response = client.get("/test/invalid-agent-name")
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "INVALID_AGENT_NAME"
    assert "invalid@name" in data["error"]["message"]
    assert data["error"]["details"]["name"] == "invalid@name"
    assert "pattern" in data["error"]["details"]
    assert "description" in data["error"]["details"]
    assert "request_id" in data["error"]
    assert "timestamp" in data["error"]


def test_agent_already_exists_error(client):
    response = client.get("/test/agent-already-exists")
    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "AGENT_ALREADY_EXISTS"
    assert "my-agent" in data["error"]["message"]
    assert data["error"]["details"]["name"] == "my-agent"
    assert "request_id" in data["error"]
    assert "timestamp" in data["error"]


def test_generic_exception_handler():
    """Test that generic_exception_handler creates properly formatted responses."""
    # Test the handler function directly since FastAPI's TestClient
    # doesn't route generic exceptions through exception handlers the same way

    # Create a mock request
    class MockRequest:
        def __init__(self):
            self.url = type("URL", (), {"path": "/test"})()

    # Call the handler directly
    request = MockRequest()
    exc = ValueError("Something unexpected")
    response = asyncio.run(generic_exception_handler(request, exc))

    assert response.status_code == 500
    data = json.loads(response.body.decode())
    assert data["error"]["code"] == "INTERNAL_ERROR"
    assert "unexpected error" in data["error"]["message"].lower()
    assert data["error"]["details"] == {}
    assert "request_id" in data["error"]
    assert "timestamp" in data["error"]


def test_error_response_structure(client):
    response = client.get("/test/thread-not-found")
    data = response.json()
    assert "error" in data
    error = data["error"]
    assert all(key in error for key in ["code", "message", "details", "request_id", "timestamp"])
