# 07 · Gotchas

> Non-obvious pitfalls specific to the RAG recipe. Read before changing the agent, env, LLM endpoint, or verify scripts.

## `CUSTOM_LLM_URL` must be a public URL

Agora cloud calls the `/llm/chat/completions` endpoint directly — not through the Next.js proxy. There is **no localhost default** by design: a `localhost` URL would let the agent "start" while its LLM calls silently fail cloud-side. Always use a public tunnel URL for local development.

## Both `CUSTOM_LLM_URL` and `CUSTOM_LLM_API_KEY` are validated at startup

`Agent.__init__` raises `ValueError` for a missing `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, `CUSTOM_LLM_URL`, or `CUSTOM_LLM_API_KEY`. The server will not boot if any of these are absent. This differs from the realtime recipe, where the OpenAI key is validated lazily at `start()`.

## `doctor:local` warns if `CUSTOM_LLM_URL` points at localhost

`bun run doctor:local` checks that `CUSTOM_LLM_URL` is set and warns (but does not fail) if it matches `localhost` or `127.0.0.1`. Treat this as an error for live usage.

## The LLM endpoint is co-public with agent token endpoints

Port 8000 serves both `/get_config`/`/startAgent`/`/stopAgent` and `/llm/chat/completions`. This is intentional for the mock. In production, move RAG logic to a dedicated service and point `CUSTOM_LLM_URL` there.

## Do not add `agora-agents` to `server/src/llm.py`

`test_llm_mount.py` performs AST inspection to assert that `llm.py` has no Agora SDK imports. The endpoint is provider-agnostic by design so it can be extracted and deployed independently.

## Do not put `PORT` in `server/.env.example`

`verify:local:fastapi` injects a random `PORT` and loads env with `load_dotenv(override=True)`. A `PORT` line in `.env.example` (copied to `.env.local`) would clobber the injected port and break the smoke test. Note also that `llm.py` uses `load_dotenv(override=False)` to avoid this problem with `CUSTOM_LLM_PORT`.

## Only streaming is supported

`POST /llm/chat/completions` rejects `stream: false` with a 400 error. Agora ConvoAI always uses streaming; do not add non-streaming support without also checking the platform contract.

## Keep `/api/*` ownership in rewrites

Adding `web/app/api/**/route.ts` for agent/token logic breaks the boundary — `verify-api-contracts.ts` explicitly fails if a `route.ts` exists under `app/api`. Token logic belongs in `server/`.

## camelCase request fields

`StartAgentRequest` uses `channelName`, `rtcUid`, `userUid` (camelCase) to match the browser client. Renaming one side without the other breaks the contract tests.

## Local calls under a global proxy

Global proxies (Clash, etc.) can break `localhost`/RFC-1918 traffic. Configure the proxy to send `127.0.0.1`, `localhost`, and private ranges DIRECT, or use `socksio` (in `requirements.txt`) plus `all_proxy` to route the backend through SOCKS.

## Related Deep Dives

- [retrieval_pipeline.md](L2/retrieval_pipeline.md) — RAG endpoint internals including the `override=False` env-loading pattern.
