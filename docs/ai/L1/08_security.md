# 08 · Security

> Trust boundaries, secret handling, and auth for the RAG recipe.

## Trust boundaries

| Hop                             | Auth                                                                          |
| ------------------------------- | ----------------------------------------------------------------------------- |
| Browser → agent backend         | None in local dev (the `/api/*` rewrite is same-origin).                      |
| Agent backend → Agora cloud     | Token007, generated from `AGORA_APP_ID` + `AGORA_APP_CERTIFICATE`.            |
| Agora cloud → `/llm` endpoint   | `Authorization: Bearer <CUSTOM_LLM_API_KEY>`. The mock does **not** validate it; a production endpoint should. |

## Secret handling

- **Server-only secrets:** `AGORA_APP_CERTIFICATE`, `CUSTOM_LLM_URL`, and `CUSTOM_LLM_API_KEY` live only in `server/.env.local` and never reach the browser. The browser receives a short-lived token, never the certificate or the LLM key.
- `server/.env.local` is gitignored; `server/.env.example` ships placeholders only.
- Tokens (`generate_convo_ai_token`) expire after 3600s and are minted per `get_config` call for a concrete non-zero UID.

## Co-public endpoint risk

Port 8000 serves both agent token endpoints and `/llm/chat/completions`. Exposing it publicly means both surfaces are reachable. Mitigations:

- The mock `/llm` endpoint does not require a valid API key (any `Authorization` header is accepted).
- In production, validate the Bearer token in `llm.py`'s `/chat/completions` route before processing.
- Move the RAG service to a dedicated host and point `CUSTOM_LLM_URL` there to separate the trust surfaces.

## CORS

The backend sets `CORSMiddleware` with `allow_origins=["*"]` — open by design for a local/dev recipe. **Lock this down to known origins before any production deployment.**

## Validation

- `Agent.__init__` raises `ValueError` for missing `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, `CUSTOM_LLM_URL`, or `CUSTOM_LLM_API_KEY` — the server will not start with incomplete credentials.
- `Agent.start()` rejects empty `channel_name` and non-positive `agent_uid`/`user_uid`.
- Route errors are sanitized: `_log_route_error` logs only non-`None` context; exceptions map to 400/500 without leaking internals to the client beyond the message.

## Deployment notes

- Set `AGENT_BACKEND_URL` only to a backend you control; the rewrite forwards browser requests there verbatim.
- Set `CUSTOM_LLM_URL` to the public URL of a service you control.
- The published Docker image is **backend-only** (`:8000`); it does not bundle secrets.

## Related Deep Dives

- None.
