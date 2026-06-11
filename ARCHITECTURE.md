# Architecture — RAG Recipe

Three processes. The browser talks only to Next.js `/api/*`, which rewrites to the
agent backend. The agent backend owns Agora tokens and agent lifecycle. The RAG LLM
endpoint is a separate service that **Agora cloud** calls directly.

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
  ▼
Agora ConvoAI Cloud
  │  user speech → Deepgram STT nova-3 (managed)
  │  POST <CUSTOM_LLM_URL>/chat/completions   (Authorization: Bearer <key>)
  ▼
RAG LLM endpoint (llm/, :8001, public via tunnel)
  │  retrieve() scores corpus topics against the query
  │  returns grounded reply: "Based on our docs: <snippet>"
  │  returns OpenAI SSE
  ▼
Agora ConvoAI Cloud → MiniMax TTS (managed) → user hears speech
                     → RTM transcript / metrics → web UI
```

`POST /api/stopAgent { agentId }` ends the session.

## RAG endpoint internals

The `llm/` server contains a small in-code `CORPUS` dict (topic → document text).
On each turn `retrieve()` scores every topic against the user query by counting
overlapping words, then returns the top-K matches (controlled by `RAG_TOP_K`).
`run_agent_turn()` turns the hits into a grounded reply or a graceful miss message.

- Retrieval is **real** keyword-based scoring code, tested in `llm/tests/test_rag.py`.
- Generation is **mocked** (no LLM API calls, zero-key).
- To use a real vector store, swap `CORPUS` and `retrieve()` in
  `llm/src/custom_llm_server.py`. The rest of the file and the HTTP contract remain
  unchanged.

## Why two backends

`server/` and `llm/` are split because of an **exposure asymmetry**:

- `llm/` must be reachable by **Agora cloud over the public internet** (hence the
  ngrok tunnel). It is the part you replace with your own RAG pipeline, and it has
  no Agora dependency.
- `server/` only needs to be reachable by your web tier. It holds the Agora App
  Certificate and all token logic.

In production the two could be co-deployed, but they are kept separate here to
make that boundary — and the public-exposure requirement — explicit.

## API (agent backend, port 8000)

| Endpoint | Method | Description |
| --- | --- | --- |
| `/get_config` | GET | Token + channel/UID config |
| `/startAgent` | POST | Start the agent session |
| `/stopAgent` | POST | Stop the agent by `agent_id` |

The browser calls these as `/api/*`; Next rewrites them to `AGENT_BACKEND_URL`.

## Auth

- Browser → agent backend: none (local dev).
- Agent backend → Agora cloud: Token007, generated from `AGORA_APP_ID` +
  `AGORA_APP_CERTIFICATE`.
- Agora cloud → RAG LLM endpoint: `Authorization: Bearer <CUSTOM_LLM_API_KEY>`.
  The mock endpoint does not validate it; a production endpoint should.
