# 05 · Workflows

> Step-by-step guides for the common changes in this recipe. Each ends with the narrowest verify command to run.

## Swap the retrieval corpus or adopt a real vector store

1. Replace `CORPUS` (dict) and `retrieve()` in `server/src/llm.py` with your vector store client.
2. Keep `run_agent_turn()` and the OpenAI SSE streaming contract unchanged.
3. A production endpoint should validate the `Authorization: Bearer` header.
4. Update `server/.env.example` if new env vars are required.
5. Verify: `cd server && pytest tests -v` (update `test_rag.py` to match the new corpus).

## Change the agent greeting or model name

1. Greeting: set `AGENT_GREETING` (env) or edit the default in `server/src/agent.py`.
2. Model: set `CUSTOM_LLM_MODEL` (default `rag-mock`); this name is passed to your endpoint.
3. Verify: `bun run verify:backend` (compile check) + `cd server && pytest tests -v`.

## Change STT or TTS vendors

1. Edit `DeepgramSTT` or `MiniMaxTTS` vendor construction in `server/src/agent.py`.
2. Verify: `bun run verify:backend` + `cd server && pytest tests -v`.

## Add or change a browser-facing route

1. Add the FastAPI handler in `server/src/server.py` (return the `{ code, msg, data }` envelope).
2. Add the `/api/<name>` → `/<name>` mapping in `web/next.config.ts` `rewrites()`.
3. Add a client helper in `web/src/services/api.ts`.
4. Extend `web/scripts/verify-api-contracts.ts` with the new path + envelope assertions.
5. Verify: `bun run verify:web` (and `bun run verify:local:fastapi` for end-to-end).

## Adjust RAG_TOP_K

Set `RAG_TOP_K` in `server/.env.local`. The module reads it at startup; restart the backend after changing it.

## Run / debug locally

```bash
bun run dev              # both processes
bun run doctor:local     # check creds + .env.local + CUSTOM_LLM_URL before a live call
```

## Verify before finishing

| Change touches…               | Run                                                                              |
| ----------------------------- | -------------------------------------------------------------------------------- |
| Web only                      | `bun run verify:web`                                                              |
| Backend logic / agent config  | `bun run verify:backend` + `cd server && pytest tests -v`                         |
| RAG retrieval / LLM endpoint  | `bun run verify:backend` + `cd server && pytest tests -v` + `bun run verify:local:llm` |
| Route/proxy boundary          | `bun run verify:web:proxy` and/or `bun run verify:local:fastapi`                 |
| Anything end-to-end (local)   | `bun run verify:local`                                                            |

## Deploy

1. Deploy `web/` as a Next.js app.
2. Deploy `server/` as a publicly reachable FastAPI service (it serves both agent tokens and `/llm`). The published backend-only image is `ghcr.io/AgoraIO-Conversational-AI/recipe-agent-rag` on `v*` tags.
3. Set `AGENT_BACKEND_URL` in the web deployment so rewrites reach the backend.
4. Set `CUSTOM_LLM_URL` to `<public-server-url>/llm/chat/completions` so Agora cloud can reach the endpoint.

> In production, consider moving RAG logic to a dedicated service and pointing `CUSTOM_LLM_URL` there, to avoid co-locating agent tokens and LLM logic on the same public URL.

## Related Deep Dives

- [retrieval_pipeline.md](L2/retrieval_pipeline.md) — full corpus and retrieval internals, SSE streaming details.
- [session_lifecycle.md](L2/session_lifecycle.md) — client-side join/renewal/teardown.
