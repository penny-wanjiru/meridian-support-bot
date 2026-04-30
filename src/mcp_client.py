import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from src.config import MCP_SERVER_URL

logger = logging.getLogger(__name__)


def _strip_titles(schema: dict) -> dict:
    """Recursively remove 'title' fields that OpenAI rejects from MCP schemas."""
    cleaned: dict = {}
    for key, value in schema.items():
        if key == "title":
            continue
        if isinstance(value, dict):
            cleaned[key] = _strip_titles(value)
        elif isinstance(value, list):
            cleaned[key] = [
                _strip_titles(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            cleaned[key] = value
    return cleaned


def mcp_tool_to_openai_function(tool) -> dict:
    schema = tool.inputSchema if tool.inputSchema else {"type": "object", "properties": {}}
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": _strip_titles(schema),
        },
    }


@asynccontextmanager
async def mcp_session():
    try:
        async with streamablehttp_client(url=MCP_SERVER_URL) as (
            read_stream,
            write_stream,
            _get_session_id,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session
    except Exception as exc:
        if isinstance(exc, (ConnectionError, OSError)):
            logger.error("Failed to connect to MCP server at %s: %s", MCP_SERVER_URL, exc)
            raise ConnectionError(f"MCP server unreachable: {exc}") from exc
        raise


async def get_openai_tools(session: ClientSession) -> list[dict]:
    result = await session.list_tools()
    tools = [mcp_tool_to_openai_function(t) for t in result.tools]
    logger.info("Discovered %d MCP tools", len(tools))
    return tools


async def execute_tool(session: ClientSession, name: str, arguments: dict[str, Any]) -> str:
    logger.info("Calling MCP tool %s with %s", name, json.dumps(arguments))
    result = await session.call_tool(name, arguments)

    parts = []
    for block in result.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    output = "\n".join(parts) if parts else "(no output)"
    logger.info("Tool %s returned %d chars", name, len(output))
    return output
