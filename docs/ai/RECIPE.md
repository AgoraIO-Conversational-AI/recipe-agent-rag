---
recipe_version: 1.0.0
recipe_status: experimental
extension_points:
  - id: rag.corpus-and-retrieval
    name: In-code CORPUS dict and retrieve() function in server/src/llm.py
  - id: agent.llm-config
    name: CustomLLM vendor url, key, model, greeting, and session parameters
  - id: web.conversation-ui
    name: Conversation UI panels and controls
  - id: verification.contracts
    name: Contract, proxy, FastAPI, and LLM smoke verification
invariants:
  - id: api.rewrite-boundary
    summary: Browser calls stay on /api/* and Next rewrites to FastAPI; no Route Handlers for agent/token logic.
  - id: secrets.server-only
    summary: Agora App Certificate, CUSTOM_LLM_URL, and CUSTOM_LLM_API_KEY stay in the Python backend.
  - id: llm.agora-free
    summary: server/src/llm.py must not import agora-agents; it is provider-agnostic and can be extracted independently.
  - id: llm.streaming-only
    summary: POST /llm/chat/completions accepts only stream=true; the OpenAI SSE format must not change.
  - id: llm.public-url
    summary: CUSTOM_LLM_URL has no localhost default; Agora cloud cannot reach a local address.
  - id: token.uid-concrete
    summary: Backend resolves missing, zero, or negative UIDs before issuing an RTC+RTM token.
stable_contracts:
  - id: env.required
    summary: AGORA_APP_ID, AGORA_APP_CERTIFICATE, CUSTOM_LLM_URL, and CUSTOM_LLM_API_KEY are required; AGENT_BACKEND_URL is required by deployed web rewrites.
  - id: api.core-routes
    summary: GET /api/get_config, POST /api/startAgent, and POST /api/stopAgent remain the browser-facing contract.
  - id: llm.core-routes
    summary: POST /llm/chat/completions and GET /llm/health remain the Agora-cloud-facing LLM contract.
  - id: response.envelope
    summary: Successful backend responses use { code, msg, data }.
---

# Recipe Contract

This base recipe defines the reusable surface for a Python-backed Agora Conversational AI **RAG** quickstart: a cascading STT→CustomLLM→TTS pipeline where the LLM stage is a public OpenAI-compatible endpoint that retrieves from a corpus and grounds replies in it.

## Recipe Role

- Role: `base` recipe (self-contained, clone-and-run; no `Extends` pin).
- Target audience: developers building a knowledge-grounded voice agent with a Python FastAPI backend, a RAG retrieval endpoint, and a Next.js web client.
- Reuse model: clone, bind project, expose backend publicly, run, then swap `CORPUS` + `retrieve()` for a real vector store.

## Recipe Scope

- Python FastAPI token generation and managed agent lifecycle using the `CustomLLM` vendor.
- A zero-key mock RAG LLM endpoint (`server/src/llm.py`) that is OpenAI-compatible, streaming-only, and Agora-SDK-free.
- Cascading STT (Deepgram nova-3) → CustomLLM → TTS (MiniMax speech_2_6_turbo) vendor chain.
- Next.js browser UI with RTC audio, RTM transcript/metrics, connection status.
- Rewrite-only `/api/*` browser facade hiding backend placement.
- Contract, proxy, FastAPI, and LLM smoke verification that need no live Agora calls.

## Baseline Implementation Guidance

Use this repo's source and progressive disclosure docs as the starting point, then customize. Do not recreate the Agora ConvoAI integration from memory — vendor schemas, SDK builder fields, token behavior, and RTM details drift. Copy verified patterns from this repo.

## Extension Points

| ID | Surface | How to extend | Required follow-up |
| -- | ------- | ------------- | ------------------ |
| `rag.corpus-and-retrieval` | `server/src/llm.py` (`CORPUS`, `retrieve()`) | Replace with real vector store client. Keep `run_agent_turn()` and HTTP SSE contract unchanged. | Update `test_rag.py`; add new env vars to `server/.env.example`; validate `Authorization` header in production. |
| `agent.llm-config` | `server/src/agent.py` (`CustomLLM`, `DeepgramSTT`, `MiniMaxTTS`) | Change `CUSTOM_LLM_URL`, `CUSTOM_LLM_MODEL`, STT/TTS vendors, `greeting_message`, `max_history`, session parameters. | Run `verify:backend` + `pytest tests`; document new env in `server/.env.example` (never add `PORT`). |
| `web.conversation-ui` | `web/src/components/*`, `web/src/lib/conversation.ts` | Customize pre-call, transcript, metrics, connection status, mic, or visualizer UI. | Preserve RTC/RTM lifecycle ownership and transcript UID normalization. |
| `verification.contracts` | `web/scripts/*.ts`, root `package.json` | Add checks for new browser/backend or Agora-cloud/LLM boundaries. | Keep checks runnable without live Agora credentials. |

## Invariants

- Browser code calls only `/api/get_config`, `/api/startAgent`, and `/api/stopAgent` for the default flow.
- Next.js owns `/api/*` through rewrites only; no `web/app/api/**/route.ts` for agent/token logic.
- FastAPI owns token generation, `AGORA_APP_CERTIFICATE`, `CUSTOM_LLM_URL`, and agent lifecycle.
- `server/src/llm.py` must not import `agora-agents`; it is provider-agnostic.
- `POST /llm/chat/completions` accepts only `stream: true`; the OpenAI SSE format (role chunk → content chunks → stop chunk → `[DONE]`) must not change.
- `CUSTOM_LLM_URL` has no localhost default; Agora cloud cannot reach a local address.
- The backend issues one RTC+RTM-capable token for a concrete non-zero UID.

## Stable Contracts

| Contract | Stable shape |
| -------- | ------------ |
| Required backend env | `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, `CUSTOM_LLM_URL`, `CUSTOM_LLM_API_KEY` |
| Optional backend env | `CUSTOM_LLM_MODEL`, `AGENT_GREETING`, `RAG_TOP_K`, `PORT` (env only) |
| Required web deploy env | `AGENT_BACKEND_URL` |
| `GET /api/get_config` | Query `channel?`, `uid?`; returns `data.app_id`, `data.token`, `data.uid`, `data.channel_name`, `data.agent_uid`. |
| `POST /api/startAgent` | Body `{ channelName, rtcUid, userUid, parameters? }`; returns `data.agent_id`, `data.channel_name`, `data.status`. |
| `POST /api/stopAgent` | Body `{ agentId }`; returns `{ code: 0, msg: "success" }`. |
| `POST /llm/chat/completions` | OpenAI-compatible streaming endpoint; `stream: true` required; `Authorization: Bearer` forwarded by Agora cloud. |
| `GET /llm/health` | Returns `{ status: "ok", service: "rag-llm-mock" }`. |
| Success envelope | `{ "code": 0, "msg": "success", "data": ... }` where the route has data. |
| Verification entry points | `bun run verify:web`, `bun run verify:backend`, `bun run verify:web:proxy`, `bun run verify:local:fastapi`, `bun run verify:local:llm`, `bun run verify:local`. |

## Internal / Subject to Change

- Visual layout, component composition, Tailwind classes, and assets under `web/src/components/`.
- Exact model names, voices, greeting text, VAD config, and `CustomLLM` parameters as long as they stay documented extension points.
- In-memory `Agent._sessions` details; the stable behavior is start by channel/user and stop by returned `agent_id`.
- Verification internals under `web/scripts/`; the stable surface is the root script names and what they assert.
- `agora-agents` SDK minor-version behavior; this recipe lower-bounds `>=2.3.0` but does not freeze every field.
- `CORPUS` content and `retrieve()` scoring heuristic; only the HTTP contract is stable.

## Related Progressive Disclosure Docs

- `L1/01_setup.md` — setup, env, ngrok, and commands.
- `L1/02_architecture.md` — request flow, single-port topology, and cascading vendor chain.
- `L1/05_workflows.md` — common modification workflows.
- `L1/06_interfaces.md` — route, rewrite, env, and LLM endpoint contracts.
- `L1/L2/retrieval_pipeline.md` — full RAG endpoint internals and SSE streaming details.
- `L1/L2/session_lifecycle.md` — RTC/RTM/session orchestration.
