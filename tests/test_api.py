"""Tests for the FastAPI endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.index import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_health_endpoint(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_chat_empty_messages(client):
    resp = await client.post("/api/chat", json={"messages": []})
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


async def test_chat_invalid_role(client):
    resp = await client.post(
        "/api/chat",
        json={"messages": [{"role": "system", "content": "hi"}]},
    )
    assert resp.status_code == 400
    assert "Invalid role" in resp.json()["detail"]


async def test_chat_success(client):
    mock_result = {"role": "assistant", "content": "Hello!"}

    with patch("src.agent.chat", new_callable=AsyncMock, return_value=mock_result):
        resp = await client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "assistant"
    assert data["content"] == "Hello!"


async def test_chat_connection_error_returns_503(client):
    with patch(
        "src.agent.chat",
        new_callable=AsyncMock,
        side_effect=ConnectionError("MCP server unreachable"),
    ):
        resp = await client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )

    assert resp.status_code == 503
    assert "unavailable" in resp.json()["detail"].lower()


async def test_chat_unexpected_error_returns_502(client):
    with patch(
        "src.agent.chat",
        new_callable=AsyncMock,
        side_effect=RuntimeError("unexpected"),
    ):
        resp = await client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )

    assert resp.status_code == 502
    assert "something went wrong" in resp.json()["detail"].lower()


async def test_chat_missing_body(client):
    resp = await client.post("/api/chat")
    assert resp.status_code == 422
