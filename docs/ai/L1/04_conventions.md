# 04 · Conventions

> Coding patterns shared across `server/` and `web/`. Follow these to keep local and deployed modes aligned, and the retrieval/streaming contracts intact.

## Boundary ownership

- Browser code calls only `/api/*`. Backend placement is hidden behind Next rewrites (`web/next.config.ts`).
- **Never** add `web/app/api/**/route.ts` for agent/token logic — `verify-api-contracts.ts` fails the build if a `route.ts` appears under `app/api`.
- Token generation and the App Certificate stay in `server/`.
- `server/src/llm.py` must remain free of `agora-agents` — `test_llm_mount.py` asserts this via AST inspection.

## Backend (Python / FastAPI)

- Async throughout: route handlers are `async def`; the agent uses `AsyncAgora` and `create_async_session`.
- Request bodies are Pydantic models (`StartAgentRequest`, `StopAgentRequest`). Field names are **camelCase** (`channelName`, `rtcUid`, `userUid`) to match the browser client.
- Error mapping is centralized: `_to_http_error()` maps `ValueError → 400`, `RuntimeError → 500`, else 500. `_log_route_error()` logs with safe context + traceback. Raise plain `ValueError`/`RuntimeError`; let the route convert.
- Logging via `logging.getLogger("uvicorn.error")`.
- Env read with `os.getenv`; `.env.local` then `.env` loaded with `override=True` in `server.py`, `override=False` in `llm.py` (so an injected `PORT` from the verify harness is not clobbered).

## Response envelope

All backend JSON responses use:

```json
{ "code": 0, "msg": "success", "data": { } }
```

`data` is present only when the route returns a payload. The browser client treats `code !== 0` (or missing `data`) as an error.

## RAG LLM endpoint (OpenAI SSE contract)

The `/llm/chat/completions` endpoint must implement the OpenAI streaming format exactly:

- Only `stream: true` is accepted; non-streaming requests return 400.
- Each chunk: `data: {json}\n\n` where the JSON contains `id`, `object`, `created`, `model`, `choices[{delta, index, finish_reason}]`.
- The first chunk sets `delta.role = "assistant"`.
- The final content chunk sets `finish_reason = "stop"`.
- The stream closes with `data: [DONE]\n\n`.

Keep `run_agent_turn()` and the SSE streaming contract unchanged when swapping corpus or retrieval logic.

## Retrieval conventions

- `retrieve(query, corpus, top_k)` — returns `[(topic, doc)]` pairs, scored by token overlap.
- `TOP_K` is read from `RAG_TOP_K` env var at module load; guarded against non-integer values.
- Replace only `CORPUS` and `retrieve()` when adopting a real vector store; leave `run_agent_turn()` and all HTTP machinery intact.

## Web (TypeScript / Next.js)

- Lint/format with Biome (`bun run lint`, `bun run lint:fix` in `web/`).
- RTC client creation must be StrictMode-safe (strict mode is on).
- Transcript speaker mapping uses real UIDs (`normalizeTranscript` maps `uid === '0'` to the local UID).
- API client lives in `src/services/api.ts`; UI never calls `fetch` to the backend directly.

## Testing approach

- Backend: `pytest` in `server/`, standalone — `conftest.py` fakes env and SDK session, so no cloud or real creds are needed.
- Web: contract/proxy/fastapi/llm smoke scripts under `web/scripts/` run without live Agora calls.
- Run the **narrowest** relevant verify command before finishing (see [05_workflows](05_workflows.md)).

## Doc upkeep

When you change request/response contracts, env vars, or workflow, update the web client, backend, contract checks, README, **and** the matching `docs/ai/L1/` file together, then bump `Last Reviewed` in [L0](../L0_repo_card.md).

## Related Deep Dives

- None.
