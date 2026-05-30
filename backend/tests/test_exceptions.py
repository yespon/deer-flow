"""Tests for API exception handling."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.exceptions import (
    APIError,
    RateLimitExceededError,
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
