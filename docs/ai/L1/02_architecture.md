# 02 · Architecture

> Single-port two-process system. The browser talks only to Next.js `/api/*`, which rewrites to the FastAPI agent backend. The backend owns Agora tokens, the agent session, **and** the RAG LLM endpoint — all on port 8000. Agora cloud calls the LLM endpoint directly, so port 8000 must be publicly reachable.

## Topology

```
Browser (localhost:3000)
  │  fetch /api/*
  ▼
Next.js (web/)  ──rewrite──▶  Agent backend (server/, :8000)
                                 │  builds AgoraAgent with CustomLLM vendor
                                 │  also mounts /llm (server/src/llm.py) — same process
                                 ▼
                              Agora ConvoAI Cloud
                                 │  user speech → Deepgram STT nova-3 (managed)
                                 │  POST <CUSTOM_LLM_URL>/chat/completions
                                 ▼
                              /llm endpoint (server/src/llm.py, public via ngrok http 8000)
                                 │  retrieve() scores corpus against the query
                                 │  run_agent_turn() returns grounded reply
                                 │  streams OpenAI SSE chunks
                                 ▼
                              Agora ConvoAI Cloud → MiniMax TTS (managed) → user hears speech
                                                  → RTM transcript / metrics → web UI
```

- **`web/`** — Next.js 16 / React 19 / TypeScript. Owns UI plus the RTC/RTM client lifecycle. Calls only `/api/*`.
- **`server/`** — Python FastAPI (:8000). Owns Agora token generation and agent session lifecycle. SDK: `agora-agents>=2.3.0` (`import agora_agent`).
- **`server/src/llm.py`** — provider-agnostic FastAPI RAG LLM endpoint mounted at `/llm`. No `agora-agents` dependency. This is the component developers replace with a real vector store.

## Request lifecycle

1. Browser `GET /api/get_config` → Next rewrites to backend `/get_config`; backend mints a Token007 from `AGORA_APP_ID` + `AGORA_APP_CERTIFICATE` and returns channel + UIDs.
2. Browser joins the RTC channel, then `POST /api/startAgent`; backend builds the `CustomLLM` vendor and starts an async agent session.
3. User speaks. Agora runs Deepgram STT (nova-3), then POSTs the transcript to `CUSTOM_LLM_URL` as an OpenAI `POST /chat/completions` request with `Authorization: Bearer <CUSTOM_LLM_API_KEY>`.
4. Inside `/llm`, `retrieve()` scores the user query against the in-code `CORPUS`. `run_agent_turn()` grounds the reply in the top-K hits and streams the result in OpenAI SSE format.
5. Agora runs MiniMax TTS on the streamed reply and plays it back in the channel.
6. RTM delivers transcript + metrics to the web UI.
7. `POST /api/stopAgent { agentId }` ends the session.

## Single-process design

`server/src/llm.py` is mounted into the FastAPI app at `/llm`:

```python
app.mount("/llm", llm_app)
```

Port 8000 serves both agent token endpoints **and** `/llm/chat/completions`. Expose port 8000 publicly and set `CUSTOM_LLM_URL=<tunnel>/llm/chat/completions`.

> **co-public caveat:** agent tokens and the LLM endpoint share the same public URL. In production, move RAG logic to a dedicated service.

## Key abstractions

- **`Agent`** (`server/src/agent.py`) — async wrapper around `AgoraAgent`; owns the `AsyncAgora` client, env, and the in-memory `_sessions` map keyed by `agent_id`.
- **`CustomLLM` vendor** — `agora_agent.agentkit.vendors.CustomLLM`; routes the LLM stage to the public `/llm/chat/completions` URL.
- **`CORPUS` + `retrieve()`** (`server/src/llm.py`) — keyword-scored in-code corpus; replace with a real vector store when ready.
- **Rewrite proxy** (`web/next.config.ts`) — the only browser→backend boundary; no Next Route Handlers for agent/token logic.

## Tech decisions

- **Cascading STT→LLM→TTS** — unlike the realtime recipe, the RAG recipe uses discrete vendor stages: Deepgram STT, `CustomLLM`, MiniMax TTS. This allows the `/llm` stage to be replaced independently.
- **Zero-key mock** — retrieval is real code; generation is mocked. No LLM API key is needed to run the full pipeline.
- **Public URL required** — `CUSTOM_LLM_URL` has no localhost default; a local URL would silently break cloud-side LLM calls.

## Related Deep Dives

- [retrieval_pipeline.md](L2/retrieval_pipeline.md) — `CORPUS`, `retrieve()`, `run_agent_turn()`, OpenAI SSE streaming, and how to swap in a real vector store.
- [session_lifecycle.md](L2/session_lifecycle.md) — browser orchestration of config + start/stop, RTC/RTM, transcript mapping.
