# Agora Conversational AI — RAG Recipe (Python)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://www.python.org/)
[![Bun](https://img.shields.io/badge/bun-latest-black)](https://bun.sh/)

The **rag** recipe in the Agora Conversational AI recipes family. The agent's LLM
stage is pointed at the `/llm` endpoint that lives inside the same backend process:
on each user query the endpoint retrieves the best-matching document from a small
in-code corpus and grounds its reply in it ("Based on our docs: …"). STT (Deepgram
nova-3) and TTS (MiniMax) stay Agora-managed.

This repo ships a **zero-key mock** RAG endpoint so you can run the full
STT → RAG LLM → TTS pipeline immediately. Retrieval is real code; generation is
mocked. Swap `CORPUS` and `retrieve()` in `server/src/llm.py` for a real vector
store when you are ready.

## Prerequisites

- [Python 3.10+](https://www.python.org/)
- [Bun](https://bun.sh/)
- [Agora CLI](https://github.com/AgoraIO/cli) — makes generating an App ID + App Certificate easy
- [ngrok](https://ngrok.com/) — the backend (including `/llm`) must be publicly reachable so Agora cloud can call it

## Run It

```bash
# 1. Install Python venv + web deps
bun run setup

# 2. Add Agora credentials (CLI), or edit server/.env.local by hand
agora login
agora project use <your-project>          # select which project to use (you may have several)
agora project env write server/.env.local # writes App ID/Certificate; keeps your CUSTOM_LLM_* lines

# 3. Expose the backend publicly (Agora cloud calls /llm/chat/completions directly)
ngrok http 8000

# 4. Add the tunnel URL to server/.env.local (use whatever domain ngrok prints —
#    today that is usually *.ngrok-free.dev)
#    CUSTOM_LLM_URL=https://<your-tunnel>.ngrok-free.dev/llm/chat/completions

# 5. Run the backend and web
bun run dev
```

Open [http://localhost:3000](http://localhost:3000) → **Start Conversation** → ask
about refunds, business hours, shipping, or warranty.

### Working from a clone

If you cloned this repo (rather than scaffolding via the Agora CLI), the steps
above are complete as written: `bun run setup` creates the Python venv and installs
web dependencies, then `bun run dev` brings up the backend and web. You still need
Agora credentials in `server/.env.local` and a public `CUSTOM_LLM_URL` tunnel
before a conversation can connect.

Services:

- Frontend — http://localhost:3000
- Backend (+ /llm) — http://localhost:8000
- API docs — http://localhost:8000/docs

## Deploy

Deploy `web` (Next.js) and `server` (a single publicly reachable FastAPI process
that also serves `/llm/chat/completions`). Set `AGENT_BACKEND_URL` in the web
deployment so the Next rewrites reach the backend.

A Docker image is published to `ghcr.io/AgoraIO-Conversational-AI/recipe-agent-rag`
on `v*` tags. It runs a single process on port 8000 — no second port needed. Point
`CUSTOM_LLM_URL` at `<public-url>/llm/chat/completions`. A local `docker run` still
needs a tunnel, because Agora cloud cannot reach `localhost`.

> **co-public caveat:** the backend serves both agent tokens and the `/llm` endpoint
> on the same public URL. This is intentional for the mock: in production, move RAG
> logic to a dedicated service and point `CUSTOM_LLM_URL` there.

## Environment variables

Backend env file: [`server/.env.example`](server/.env.example).

| Variable | Required | Default | Notes |
| --- | :---: | :---: | --- |
| `AGORA_APP_ID` | ✅ | — | Agora Console → Project → App ID |
| `AGORA_APP_CERTIFICATE` | ✅ | — | Agora Console → Project → App Certificate |
| `CUSTOM_LLM_URL` | ✅ | — | **Public** URL of the `/llm/chat/completions` endpoint. Agora cloud calls it; cannot be `localhost`. |
| `CUSTOM_LLM_API_KEY` | ✅ | `any-key-here` | Forwarded by Agora cloud as `Authorization: Bearer`. Required by the `CustomLLM` vendor. |
| `CUSTOM_LLM_MODEL` | | `rag-mock` | Model name passed to your endpoint |
| `AGENT_GREETING` | | built-in | Optional opening line override |
| `RAG_TOP_K` | | `1` | Number of corpus docs to retrieve per query |
| `AGENT_BACKEND_URL` (web deploy) | ✅ | — | Required in a deployed `web` app when proxying to the backend |

## Commands

```bash
bun run setup            # install web deps + create server/ venv
bun run dev              # run backend (:8000, including /llm) + web (:3000)

bun run doctor           # prerequisite check (no creds needed)
bun run doctor:local     # + .env.local + credentials + CUSTOM_LLM_URL checks

bun run verify           # web-only gate (no Agora creds needed)
bun run verify:local     # full local gate: backend compile + smoke tests + web build
bun run clean            # remove venv and build artifacts
```

Tests run standalone (no Agora cloud needed): `pytest` in `server/`, plus
`bun run verify` in `web/`. CI runs them on Linux/macOS/Windows × Python 3.10 & 3.13.

## Architecture

```
Browser (localhost:3000)
  │  fetch /api/*
  ▼
Next.js  ──rewrite──▶  Agent backend  (server/, localhost:8000)
                          │  starts agent session (CustomLLM vendor)
                          │  also serves /llm/chat/completions (same process)
                          ▼
                       Agora ConvoAI Cloud
                          │  POST <CUSTOM_LLM_URL>   (Authorization: Bearer)
                          ▼
                       /llm endpoint  (server/src/llm.py, mounted at /llm)
                          ▲  public via ngrok tunnel (ngrok http 8000)
```

The browser only ever calls Next `/api/*`, which rewrites to the agent backend.
The agent backend owns Agora tokens and agent lifecycle. The **RAG LLM endpoint**
is mounted at `/llm` in the same process — expose port 8000 publicly and set
`CUSTOM_LLM_URL=<tunnel>/llm/chat/completions`. See [ARCHITECTURE.md](./ARCHITECTURE.md).

## What You Get

- A **Next.js** web client (:3000) that drives the RTC/RTM lifecycle and only
  ever calls `/api/*`.
- A **FastAPI** agent backend (:8000) that owns Agora token generation and the
  agent session lifecycle.
- The `/api/get_config` · `/api/startAgent` · `/api/stopAgent` contract between
  the web client and the backend (Next rewrites, no Route Handlers).
- The `/llm` endpoint retrieves the best-matching document from an in-code corpus
  and grounds the reply in it; Agora cloud receives only the final spoken response.
- A **zero-key mock** so the full pipeline runs with no LLM API key.

## How It Works

1. The browser calls `/api/get_config`, which Next rewrites to the backend; the
   backend mints an Agora token from `AGORA_APP_ID` + `AGORA_APP_CERTIFICATE`.
2. The browser joins the RTC channel, then calls `/api/startAgent`; the backend
   starts an agent session using the `CustomLLM` vendor pointed at
   `CUSTOM_LLM_URL`.
3. The user speaks. Agora runs STT (Deepgram nova-3), then sends the transcript
   to the `/llm` endpoint as an OpenAI `POST /chat/completions` request,
   forwarding `CUSTOM_LLM_API_KEY` as `Authorization: Bearer`.
4. Inside the endpoint, `retrieve()` scores the user query against the in-code
   `CORPUS` and returns the top-`RAG_TOP_K` documents. `run_agent_turn()` grounds
   the reply in those documents and streams the result in the OpenAI SSE chunk
   format ("Based on our docs: …").
5. Agora runs TTS (MiniMax) on the streamed reply and plays it back in the
   channel.
6. `/api/stopAgent` ends the session.

### Replacing the mock

Swap `CORPUS` and `retrieve()` in [`server/src/llm.py`](server/src/llm.py) for a
real vector store (e.g. ChromaDB, pgvector, Pinecone). The `run_agent_turn()`
function and the OpenAI streaming contract must remain unchanged. A production
endpoint should also validate the `Authorization: Bearer` header.

## Repo Map

- `web/` — Next.js frontend (:3000); RTC/RTM lifecycle and UI.
- `server/` — FastAPI agent backend (:8000); Agora tokens + agent lifecycle, `CustomLLM` vendor, and `/llm` mock endpoint.
- `ARCHITECTURE.md` — system shape and component boundaries.
- `AGENTS.md` — guide for coding agents working in this repo.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Agent starts but never speaks | `CUSTOM_LLM_URL` is not public or omits `/llm/chat/completions`. Use your ngrok URL. |
| `doctor:local` warns about localhost | Replace the local URL with your public tunnel URL. |
| Local calls fail / hang under a global proxy (Clash, etc.) | Configure it to send `127.0.0.1`, `localhost`, and RFC-1918 ranges DIRECT. |

## More Docs

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [AGENTS.md](./AGENTS.md)

## License

Released under the [MIT License](./LICENSE).
