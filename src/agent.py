"""Chat agent that combines OpenAI GPT-4o-mini with MCP tools."""

import json
import logging

from openai import AsyncOpenAI

from src.config import OPENAI_API_KEY, OPENAI_MODEL, MAX_TOOL_ROUNDS
from src.mcp_client import mcp_session, get_openai_tools, execute_tool
from src.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def chat(messages: list[dict]) -> dict:
    """Process a chat turn: send messages to GPT-4o-mini, execute tool calls via MCP, and return the final assistant message.

    Args:
        messages: Conversation history from the client (list of {role, content} dicts).

    Returns:
        A single {role, content} dict with the assistant's reply.
    """
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    async with mcp_session() as session:
        tools = await get_openai_tools(session)

        for round_num in range(MAX_TOOL_ROUNDS):
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=full_messages,
                tools=tools if tools else None,
            )

            choice = response.choices[0]
            assistant_message = choice.message

            # If the model didn't call any tools, we're done
            if not assistant_message.tool_calls:
                return {
                    "role": "assistant",
                    "content": assistant_message.content or "",
                }

            # Append the assistant message (with tool_calls) to the conversation
            full_messages.append(assistant_message.model_dump())

            # Execute each tool call and append results
            for tool_call in assistant_message.tool_calls:
                fn = tool_call.function
                try:
                    arguments = json.loads(fn.arguments)
                    result = await execute_tool(session, fn.name, arguments)
                except Exception as exc:
                    logger.error("Tool %s failed: %s", fn.name, exc)
                    result = f"Error executing tool: {exc}"

                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

            logger.info("Completed tool-calling round %d", round_num + 1)

    # If we exhausted all rounds, return a graceful fallback
    logger.warning("Exhausted %d tool-calling rounds", MAX_TOOL_ROUNDS)
    return {
        "role": "assistant",
        "content": "I'm sorry, I wasn't able to complete your request. Could you try rephrasing or simplifying your question?",
    }
