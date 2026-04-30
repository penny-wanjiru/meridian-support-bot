import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

app = FastAPI(title="Meridian Electronics Support Chat")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "public"


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


class ChatResponse(BaseModel):
    role: str
    content: str


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages list cannot be empty")

    for msg in request.messages:
        if msg.role not in ("user", "assistant"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role '{msg.role}'. Must be 'user' or 'assistant'.",
            )

    from src.agent import chat

    try:
        messages_dicts = [m.model_dump() for m in request.messages]
        result = await chat(messages_dicts)
        return ChatResponse(**result)
    except ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Our backend systems are temporarily unavailable. Please try again shortly.",
        )
    except Exception as exc:
        logging.getLogger(__name__).error("Chat failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=502,
            detail="Sorry, something went wrong processing your request. Please try again.",
        )


@app.get("/", include_in_schema=False)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    return RedirectResponse(url="/index.html", status_code=307)
