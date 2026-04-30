"""Tests for the chat agent module."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.agent import chat


def _make_openai_response(content=None, tool_calls=None):
    """Helper to build a mock OpenAI ChatCompletion response."""
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    if tool_calls:
        message.model_dump = lambda: {
            "role": "assistant",
            "content": content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ],
        }
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def _make_tool_call(call_id, name, arguments):
    fn = SimpleNamespace(name=name, arguments=json.dumps(arguments))
    return SimpleNamespace(id=call_id, function=fn)


@pytest.mark.asyncio
async def test_simple_response_no_tools():
    """When the model returns text without tool calls, return it directly."""
    mock_response = _make_openai_response(content="Hello! How can I help?")

    with (
        patch("src.agent.mcp_session") as mock_mcp,
        patch("src.agent.get_openai_tools", new_callable=AsyncMock, return_value=[]),
        patch.object(
            __import__("src.agent", fromlist=["client"]).client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ),
    ):
        mock_session = AsyncMock()
        mock_mcp.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_mcp.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await chat([{"role": "user", "content": "Hi"}])

    assert result["role"] == "assistant"
    assert result["content"] == "Hello! How can I help?"


@pytest.mark.asyncio
async def test_tool_calling_round():
    """When the model calls a tool, execute it and return the final text."""
    tool_call = _make_tool_call("tc_1", "list_products", {})
    response_with_tool = _make_openai_response(content=None, tool_calls=[tool_call])
    response_final = _make_openai_response(content="Here are our products: ...")

    with (
        patch("src.agent.mcp_session") as mock_mcp,
        patch("src.agent.get_openai_tools", new_callable=AsyncMock, return_value=[{"type": "function", "function": {"name": "list_products"}}]),
        patch("src.agent.execute_tool", new_callable=AsyncMock, return_value='[{"name":"Monitor"}]'),
        patch.object(
            __import__("src.agent", fromlist=["client"]).client.chat.completions,
            "create",
            new_callable=AsyncMock,
            side_effect=[response_with_tool, response_final],
        ),
    ):
        mock_session = AsyncMock()
        mock_mcp.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_mcp.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await chat([{"role": "user", "content": "Show products"}])

    assert result["role"] == "assistant"
    assert "products" in result["content"].lower()


@pytest.mark.asyncio
async def test_max_rounds_exhausted():
    """When tool-calling rounds are exhausted, return a fallback message."""
    tool_call = _make_tool_call("tc_loop", "search_products", {"query": "x"})
    looping_response = _make_openai_response(content=None, tool_calls=[tool_call])

    with (
        patch("src.agent.mcp_session") as mock_mcp,
        patch("src.agent.get_openai_tools", new_callable=AsyncMock, return_value=[]),
        patch("src.agent.execute_tool", new_callable=AsyncMock, return_value="[]"),
        patch("src.agent.MAX_TOOL_ROUNDS", 2),
        patch.object(
            __import__("src.agent", fromlist=["client"]).client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=looping_response,
        ),
    ):
        mock_session = AsyncMock()
        mock_mcp.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_mcp.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await chat([{"role": "user", "content": "Loop forever"}])

    assert result["role"] == "assistant"
    assert "sorry" in result["content"].lower()
