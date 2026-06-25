# 06 · Interfaces

> Boundary contracts: backend routes, the `/api/*` rewrite map, env vars, the response envelope, and the RAG LLM endpoint contract.

## Backend routes (port 8000)

The browser calls the agent routes as `/api/<name>`; Next rewrites to the backend `/<name>`. Agora cloud calls the LLM route directly via `CUSTOM_LLM_URL`.

### `GET /get_config`

- Query (optional): `channel?: string`, `uid?: int` (≤ 0 or missing → backend generates one).
- Returns `data`: `{ app_id, token, uid (string), channel_name, agent_uid (string) }`.
- Token is a Token007 RTC+RTM token, expiry 3600s, for a concrete non-zero UID.

### `POST /startAgent`

- Body: `{ channelName: string, rtcUid: int, userUid: int, parameters?: object }`.
  - `parameters.output_audio_codec?: string` is the only honored parameter field.
- Returns `data`: `{ agent_id, channel_name, status: "started" }`.
- 400 if `channelName`/`rtcUid`/`userUid` invalid, or `AGORA_APP_ID`/`AGORA_APP_CERTIFICATE`/`CUSTOM_LLM_URL` missing.

### `POST /stopAgent`

- Body: `{ agentId: string }`.
- Returns `{ code: 0, msg: "success" }` (no `data`).

### `POST /llm/chat/completions`

- Called by Agora cloud, not the browser.
- Header: `Authorization: Bearer <CUSTOM_LLM_API_KEY>`.
- Body: OpenAI `ChatCompletionRequest` with `stream: true` (required).
- Response: `text/event-stream` SSE chunks in OpenAI format, ending with `data: [DONE]`.
- 400 if `stream: false`.

### `GET /llm/health`

- Returns `{ status: "ok", service: "rag-llm-mock" }`.

## Response envelope

```json
{ "code": 0, "msg": "success", "data": { } }
```

`data` omitted when the route has no payload. Non-zero `code` or missing `data` = error on the client side.

## Rewrite map (`web/next.config.ts`)

| Browser path        | Backend destination |
| ------------------- | ------------------- |
| `/api/get_config`   | `/get_config`       |
| `/api/startAgent`   | `/startAgent`       |
| `/api/stopAgent`    | `/stopAgent`        |

`rewrites()` returns `[]` when `AGENT_BACKEND_URL` is unset.

## Browser API client (`web/src/services/api.ts`)

- `getConfig({ channel?, uid? }) → GetConfigResponse`
- `startAgent(channelName, rtcUid, userUid) → agent_id`
- `stopAgent(agentId) → void`

## Environment variables

| Variable                | Scope          | Required | Default                   |
| ----------------------- | -------------- | :------: | ------------------------- |
| `AGORA_APP_ID`          | backend        |    ✅    | —                         |
| `AGORA_APP_CERTIFICATE` | backend        |    ✅    | —                         |
| `CUSTOM_LLM_URL`        | backend        |    ✅    | — (validated at `Agent.__init__`) |
| `CUSTOM_LLM_API_KEY`    | backend        |    ✅    | `any-key-here` (validated at `Agent.__init__`) |
| `CUSTOM_LLM_MODEL`      | backend        |          | `rag-mock`                |
| `AGENT_GREETING`        | backend        |          | built-in line             |
| `RAG_TOP_K`             | backend        |          | `1`                       |
| `AGENT_BACKEND_URL`     | web (deploy)   |    ✅\*  | `http://localhost:8000` (dev) |
| `PORT`                  | backend (env only) |      | `8000` — do **not** put in `.env.example` |

\* Required wherever the web app is deployed; rewrites are empty without it.

## `CustomLLM` vendor config (`agent.py`)

`CustomLLM(base_url, api_key, model, greeting_message, failure_message, max_history, max_tokens, temperature, top_p)` produces the vendor config that points Agora's LLM stage at the public RAG endpoint.

- `base_url` = `CUSTOM_LLM_URL` (must be public; no localhost default).
- `api_key` = `CUSTOM_LLM_API_KEY` (forwarded by Agora cloud as `Authorization: Bearer`).
- `model` = `CUSTOM_LLM_MODEL` (default `rag-mock`).

## Related Deep Dives

- [retrieval_pipeline.md](L2/retrieval_pipeline.md) — full RAG endpoint internals and SSE contract.
