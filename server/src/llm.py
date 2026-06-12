"""
RAG LLM Server — Mock Implementation

This server demonstrates how to implement an OpenAI-compatible Chat Completions
endpoint that works with Agora Conversational AI Engine using retrieval-augmented
generation.

Key points:
- Must implement POST /chat/completions
- Must support streaming responses (Server-Sent Events)
- Must follow OpenAI Chat Completions response format
- Agora cloud sends Authorization header with the api_key you configured

This mock version retrieves the best-matching document from an in-code corpus
and grounds its reply in it ("Based on our docs: …"). Retrieval is real code;
generation is mocked (no LLM API key needed).

Replace the mock logic with your own:
- Swap CORPUS + retrieve() for a real vector store (ChromaDB, pgvector, Pinecone)
- Keep run_agent_turn() and the OpenAI streaming contract unchanged
"""
import asyncio
import json
import logging
import os
import re
import time
import uuid
from typing import Dict, List, Optional, Union

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Load environment variables.
# override=False so an explicitly-exported value (e.g. CUSTOM_LLM_PORT injected by
# the verify:local:llm harness, or a process manager) takes precedence over a
# checked-in .env.local. In normal `dev` no port is exported, so .env.local wins.
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_base_dir, ".env.local"), override=False)
load_dotenv(os.path.join(_base_dir, ".env"), override=False)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG LLM Server (Mock)",
    description=(
        "OpenAI-compatible Chat Completions endpoint for Agora Conversational AI Engine. "
        "Retrieves matching docs from an in-code corpus and grounds replies in them."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Request Models — These match what Agora ConvoAI Engine sends
# =============================================================================

class TextContent(BaseModel):
    type: str = "text"
    text: str


class SystemMessage(BaseModel):
    role: str = "system"
    content: Union[str, List[str]]


class UserMessage(BaseModel):
    role: str = "user"
    content: Union[str, List[Union[TextContent, Dict]]]


class AssistantMessage(BaseModel):
    role: str = "assistant"
    content: Union[str, List[TextContent], None] = None
    tool_calls: Optional[List[Dict]] = None


class ToolMessage(BaseModel):
    role: str = "tool"
    content: Union[str, List[str]]
    tool_call_id: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Union[SystemMessage, UserMessage, AssistantMessage, ToolMessage]]
    stream: bool = True
    stream_options: Optional[Dict] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict]] = None
    tool_choice: Optional[Union[str, Dict]] = None
    response_format: Optional[Dict] = None


# =============================================================================
# Retrieval-augmented generation (mock, zero-key). Retrieval is real; generation
# is mocked. Replace CORPUS + retrieve() with a real vector store.
# =============================================================================

CORPUS = {
    "refund policy": "Refunds are available within 30 days of purchase with your receipt.",
    "business hours": "We are open Monday to Friday, 9 a.m. to 6 p.m.",
    "shipping": "Standard shipping takes three to five business days.",
    "warranty": "Every product includes a one-year limited warranty.",
}
try:
    TOP_K = max(1, int(os.getenv("RAG_TOP_K", "1")))
except (TypeError, ValueError):
    TOP_K = 1


def retrieve(query: str, corpus: dict = CORPUS, top_k: int = TOP_K) -> list:
    """Return up to top_k (topic, doc) pairs whose topic words appear in the query."""
    words = set(re.findall(r"[a-z0-9]+", query.lower()))
    scored = []
    for topic, doc in corpus.items():
        score = sum(1 for word in topic.split() if word in words)
        if score > 0:
            scored.append((score, topic, doc))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [(topic, doc) for _, topic, doc in scored[:top_k]]


def _extract_last_user_text(messages: list) -> str:
    for msg in reversed(messages):
        if getattr(msg, "role", None) == "user":
            content = msg.content
            if isinstance(content, str):
                return content
            if isinstance(content, list) and content:
                first = content[0]
                if isinstance(first, dict):
                    return first.get("text", "")
                if hasattr(first, "text"):
                    return first.text
            return ""
    return ""


def run_agent_turn(messages: list) -> str:
    hits = retrieve(_extract_last_user_text(messages))
    if not hits:
        topics = ", ".join(corpus_key for corpus_key in CORPUS)
        return f"I don't have anything on that yet. You can ask about: {topics}."
    snippets = " ".join(doc for _, doc in hits)
    return f"Based on our docs: {snippets}"


# =============================================================================
# Streaming Response — Must follow OpenAI SSE format exactly
# =============================================================================
# Agora ConvoAI Engine expects:
# 1. Each chunk as "data: {json}\n\n"
# 2. Final "data: [DONE]\n\n"
# 3. Each chunk has: id, object, created, model, choices[{delta, index, finish_reason}]
# =============================================================================

def make_chunk(chunk_id: str, model: str, content: str, finish_reason=None) -> str:
    """Build a single SSE chunk in OpenAI format."""
    chunk = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model or "rag-mock",
        "choices": [
            {
                "index": 0,
                "delta": {"content": content} if content else {},
                "finish_reason": finish_reason,
            }
        ],
    }
    return f"data: {json.dumps(chunk)}\n\n"


def make_role_chunk(chunk_id: str, model: str) -> str:
    """First chunk that sets the assistant role."""
    chunk = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model or "rag-mock",
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant", "content": ""},
                "finish_reason": None,
            }
        ],
    }
    return f"data: {json.dumps(chunk)}\n\n"


@app.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """
    OpenAI-compatible chat completions endpoint.

    This is the endpoint that Agora Conversational AI Engine calls.
    It must:
    - Accept the OpenAI Chat Completions request format
    - Return streaming SSE responses in OpenAI chunk format
    - End with "data: [DONE]"
    """
    logger.info(
        f"Received request: model={request.model}, "
        f"messages={len(request.messages)}, stream={request.stream}"
    )

    # Agora ConvoAI always uses streaming
    if not request.stream:
        raise HTTPException(
            status_code=400,
            detail="Only streaming mode is supported. Set stream=true.",
        )

    # Generate RAG response
    response_text = run_agent_turn(request.messages)
    chunk_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    model = request.model or "mock-model"

    async def generate():
        """Stream the response word by word to simulate real LLM behavior."""
        # First chunk: role
        yield make_role_chunk(chunk_id, model)

        # Stream content word by word with small delays (simulates token generation)
        words = response_text.split(" ")
        for i, word in enumerate(words):
            token = word if i == 0 else f" {word}"
            yield make_chunk(chunk_id, model, token)
            await asyncio.sleep(0.05)  # 50ms per token, ~realistic speed

        # Final chunk: finish_reason
        yield make_chunk(chunk_id, model, "", finish_reason="stop")
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "rag-llm-mock"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting RAG LLM Server (Mock) on port {port}")
    logger.info("This server grounds replies in an in-code corpus — no LLM API key needed.")
    logger.info(f"Endpoint: http://0.0.0.0:{port}/chat/completions")
    uvicorn.run(app, host="0.0.0.0", port=port)
