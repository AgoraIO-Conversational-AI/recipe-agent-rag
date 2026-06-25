# 03 · Code Map

> Where things live. Two top-level modules: `web/` (Next.js client) and `server/` (FastAPI backend + RAG LLM endpoint). Orchestration is in the root `package.json`.

## Root

| Path                  | Responsibility                                                               |
| --------------------- | ---------------------------------------------------------------------------- |
| `package.json`        | Bun workspace; `setup`, `dev`, `doctor*`, `verify*`, `clean` scripts.        |
| `README.md`           | Setup, run modes, env, architecture overview, troubleshooting.               |
| `ARCHITECTURE.md`     | Single-port topology and component boundaries.                               |
| `AGENTS.md`           | Coding-agent handbook + Git Conventions + Doc Commands.                      |
| `Dockerfile`          | Backend-only image (`:8000`); runs `server/src/server.py`.                   |
| `.github/workflows/`  | `ci.yml` (backend pytest matrix + web verify), `docker.yml`, `nightly.yml`. |

## `server/` — FastAPI backend (:8000)

| Path                                   | Responsibility                                                              |
| -------------------------------------- | --------------------------------------------------------------------------- |
| `src/server.py`                        | FastAPI app, CORS, token + agent routes, mounts `/llm`, uvicorn entrypoint. |
| `src/agent.py`                         | `Agent` class: `AsyncAgora` client, `start()`/`stop()`, `_sessions`.        |
| `src/llm.py`                           | RAG LLM endpoint: `CORPUS`, `retrieve()`, `run_agent_turn()`, SSE streaming. No `agora-agents` dependency. |
| `scripts/run_fake_server.py`           | Boots `server.app` with a `FakeAgent` for the local FastAPI smoke test.     |
| `tests/test_agent_construction.py`     | Builds the real `AgoraAgent`, fakes the SDK session, asserts shape.         |
| `tests/test_llm.py`                    | Contract tests for the `/chat/completions` and `/health` endpoints in isolation. |
| `tests/test_llm_mount.py`              | Asserts `/llm/health` and `/llm/chat/completions` are reachable through the server mount; also asserts `llm.py` has no Agora dependency. |
| `tests/test_rag.py`                    | Unit tests for `retrieve()` and `run_agent_turn()` logic.                   |
| `tests/conftest.py`                    | `fake_env` fixture + `FakeAgent`; no cloud, no real creds.                  |
| `.env.example`                         | Env template (do not add `PORT`).                                           |
| `requirements*.txt`                    | Runtime + dev (pytest, httpx) deps.                                         |

## `server/src/server.py` routes

- `GET /get_config` — token + channel/UID config.
- `POST /startAgent` — start the RAG agent session with `CustomLLM` vendor.
- `POST /stopAgent` — stop by `agent_id`.
- `POST /llm/chat/completions` — OpenAI-compatible RAG endpoint (Agora cloud calls this).
- `GET /llm/health` — health check for the RAG endpoint.

## `web/` — Next.js client (:3000)

| Path                                      | Responsibility                                                      |
| ----------------------------------------- | ------------------------------------------------------------------- |
| `next.config.ts`                          | `/api/*` rewrites to `AGENT_BACKEND_URL`; strict mode; Turbopack root. |
| `src/services/api.ts`                     | Browser API client: `getConfig`, `startAgent`, `stopAgent`.         |
| `src/lib/conversation.ts`                 | Transcript normalization, timestamp mapping, visualizer state.      |
| `src/lib/agora.ts`                        | Agora RTC/RTM helpers.                                              |
| `src/lib/utils.ts`                        | General utility helpers.                                            |
| `src/components/LandingPage.tsx`          | Conversation entry: config fetch, agent start, RTM login, teardown. |
| `src/components/ConversationComponent.tsx`| RTC join, mic publish, transcript/metrics/state listeners.          |
| `scripts/verify-api-contracts.ts`         | Asserts rewrites + client paths + response envelope (no network).   |
| `scripts/verify-local-proxy.ts`           | Stub backend; proxies `/api/*` through the rewrite map.             |
| `scripts/verify-local-fastapi.ts`         | Spawns real FastAPI with `FakeAgent`; proxies routes end-to-end.    |
| `scripts/verify-local-llm.ts`             | Spawns the `/llm` endpoint standalone; asserts SSE contract.        |
| `scripts/doctor.ts`                       | Web prerequisite check.                                             |

## Related Deep Dives

- None. For runtime flow see [02_architecture](02_architecture.md); for contracts see [06_interfaces](06_interfaces.md).
