# Architecture — RAG Recipe

Two processes. The browser talks only to Next.js `/api/*`, which rewrites to the
agent backend. The agent backend owns Agora tokens, agent lifecycle, **and** the
RAG LLM endpoint — all in one process on port 8000.

## Request flow

```
Browser
  │  GET /api/get_config            → token + channel/UIDs
  │  POST /api/startAgent           → start agent session
  ▼
Next.js  (rewrites /api/* → AGENT_BACKEND_URL)
  ▼
Agent backend (server/, :8000)
  │  builds session with CustomLLM(base_url=CUSTOM_LLM_URL)
  │  also mounts /llm (server/src/llm.py) — same process, same port
  ▼
Agora ConvoAI Cloud
  │  user speech → Deepgram STT nova-3 (managed)
  │  POST <CUSTOM_LLM_URL>/chat/completions   (Authorization: Bearer <key>)
  ▼
/llm endpoint (server/src/llm.py, mounted at /llm, public via ngrok http 8000)
  │  retrieve() scores corpus topics against the query
  │  returns grounded reply: "Based on our docs: <snippet>"
  │  returns OpenAI SSE
  ▼
Agora ConvoAI Cloud → MiniMax TTS (managed) → user hears speech
                     → RTM transcript / metrics → web UI
```

`POST /api/stopAgent { agentId }` ends the session.

## RAG endpoint internals

`server/src/llm.py` contains a small in-code `CORPUS` dict (topic → document text).
On each turn `retrieve()` scores every topic against the user query by counting
overlapping words, then returns the top-K matches (controlled by `RAG_TOP_K`).
`run_agent_turn()` turns the hits into a grounded reply or a graceful miss message.

- Retrieval is **real** keyword-based scoring code, tested in `server/tests/test_rag.py`.
- Generation is **mocked** (no LLM API calls, zero-key).
- To use a real vector store, swap `CORPUS` and `retrieve()` in
  `server/src/llm.py`. The rest of the file and the HTTP contract remain unchanged.

## Single-process design

`server/src/llm.py` is mounted into the FastAPI app at `/llm`:

```python
app.mount("/llm", llm_app)
```

This means port 8000 serves both the agent token endpoints **and**
`/llm/chat/completions`. Expose port 8000 publicly (e.g. `ngrok http 8000`) and
set `CUSTOM_LLM_URL=<tunnel>/llm/chat/completions`.

> **co-public caveat:** the backend serves both agent tokens and the `/llm`
> endpoint on the same public URL. In production, move RAG logic to a dedicated
> service and point `CUSTOM_LLM_URL` there.

## API (agent backend, port 8000)

| Endpoint | Method | Description |
| --- | --- | --- |
| `/get_config` | GET | Token + channel/UID config |
| `/startAgent` | POST | Start the agent session |
| `/stopAgent` | POST | Stop the agent by `agent_id` |
| `/llm/chat/completions` | POST | OpenAI-compatible RAG endpoint (Agora cloud calls this) |
| `/llm/health` | GET | Health check for the RAG endpoint |

The browser calls the first three as `/api/*`; Next rewrites them to `AGENT_BACKEND_URL`.

## Auth

- Browser → agent backend: none (local dev).
- Agent backend → Agora cloud: Token007, generated from `AGORA_APP_ID` +
  `AGORA_APP_CERTIFICATE`.
- Agora cloud → `/llm` endpoint: `Authorization: Bearer <CUSTOM_LLM_API_KEY>`.
  The mock endpoint does not validate it; a production endpoint should.
