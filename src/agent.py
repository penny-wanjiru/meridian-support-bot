import json
import logging

from openai import AsyncOpenAI

from src.config import OPENAI_API_KEY, OPENAI_MODEL, MAX_TOOL_ROUNDS
from src.mcp_client import mcp_session, get_openai_tools, execute_tool
from src.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def chat(messages: list[dict]) -> dict:
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    async with mcp_session() as session:
        tools = await get_openai_tools(session)

        for round_num in range(MAX_TOOL_ROUNDS):
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=full_messages,
                tools=tools if tools else None,
            )

            assistant_message = response.choices[0].message

            if not assistant_message.tool_calls:
                return {
                    "role": "assistant",
                    "content": assistant_message.content or "",
                }

            full_messages.append(assistant_message.model_dump())

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

    logger.warning("Exhausted %d tool-calling rounds", MAX_TOOL_ROUNDS)
    return {
        "role": "assistant",
        "content": "I'm sorry, I wasn't able to complete your request. Could you try rephrasing or simplifying your question?",
    }
