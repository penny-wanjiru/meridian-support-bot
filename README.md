# Meridian Electronics — Customer Support Chatbot

An AI-powered customer support chatbot for Meridian Electronics that helps customers browse products, place orders, and manage their accounts. Built with GPT-4o-mini and connected to internal business systems via the Model Context Protocol (MCP).

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Browser (public/index.html)                                 │
│  Vanilla JS chat UI with markdown rendering                  │
└──────────────────────┬───────────────────────────────────────┘
                       │ POST /api/chat
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  FastAPI (api/index.py)                                      │
│  Request validation, error handling, CORS                    │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  Agent (src/agent.py)                                        │
│  Agentic loop: sends messages to GPT-4o-mini, executes       │
│  tool calls via MCP, iterates until a final text response    │
└────────────┬─────────────────────────────┬───────────────────┘
             │                             │
             ▼                             ▼
┌────────────────────────┐   ┌─────────────────────────────────┐
│  OpenAI API            │   │  MCP Server (external)          │
│  GPT-4o-mini           │   │  Streamable HTTP transport      │
│  Function calling      │   │  Tools: list_products,          │
└────────────────────────┘   │  search_products, get_product,  │
                             │  verify_customer_pin,           │
                             │  list_orders, get_order,        │
                             │  create_order, ...              │
                             └─────────────────────────────────┘
```

### Key Design Decisions

- **Agentic tool-calling loop** — The agent iterates up to `MAX_TOOL_ROUNDS` (default 10), allowing multi-step workflows like authenticate → look up order → respond.
- **MCP integration** — Tools are discovered dynamically at runtime from the MCP server, so the chatbot adapts automatically if the backend team adds new capabilities.
- **Cost-effective model** — Uses GPT-4o-mini to keep per-conversation costs low while maintaining quality.
- **Clean separation** — Config, prompts, MCP client, and agent logic are each isolated in `src/`, making the codebase easy to extend or swap components.

## Project Structure

```
├── api/
│   └── index.py            # FastAPI app (Vercel serverless entrypoint)
├── src/
│   ├── agent.py            # Agentic chat loop (OpenAI + MCP tools)
│   ├── config.py           # Environment config with dotenv
│   ├── mcp_client.py       # MCP session management and tool conversion
│   └── prompts.py          # System prompt
├── public/
│   └── index.html          # Chat UI (served as static on Vercel)
├── tests/
│   ├── conftest.py         # Shared fixtures
│   ├── test_agent.py       # Agent loop tests
│   ├── test_api.py         # FastAPI endpoint tests
│   └── test_mcp_client.py  # MCP utility tests
├── vercel.json             # Vercel deployment config
├── requirements.txt        # Python dependencies
└── pyproject.toml          # Pytest configuration
```

## Getting Started

### Prerequisites

- Python 3.12+
- An OpenAI API key

### Setup

```bash
# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Model to use for chat completions |
| `MCP_SERVER_URL` | No | (built-in) | MCP server endpoint URL |
| `MAX_TOOL_ROUNDS` | No | `10` | Max tool-calling iterations per request |

### Run Locally

```bash
source .venv/bin/activate
uvicorn api.index:app --reload --port 8000
```

Open http://localhost:8000 in your browser.

### Run Tests

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

## Deployment

Configured for **Vercel** with Python serverless functions:

- `vercel.json` routes `/api/*` to the FastAPI handler
- Static files in `public/` are served directly by Vercel's CDN
- Environment variables should be set in the Vercel dashboard

## Supported Workflows

- **Product browsing** — List all products, search by keyword, view product details
- **Order lookup** — Authenticate with email + PIN, then view order history or specific orders
- **Order placement** — Authenticate, confirm items, and create a new order
- **General support** — Answer questions about Meridian Electronics products and services
