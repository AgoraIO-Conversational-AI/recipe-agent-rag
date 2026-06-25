# recipe-agent-rag — Repo Card

> Next.js web client + Python FastAPI backend for an Agora Conversational AI voice agent with a retrieval-augmented generation LLM endpoint. STT and TTS are Agora-managed; the LLM stage is a public OpenAI-compatible endpoint that retrieves from a corpus and grounds replies in it.

## Identity

| Field          | Value                                                                          |
| -------------- | ------------------------------------------------------------------------------ |
| Repo           | `AgoraIO-Conversational-AI/recipe-agent-rag`                                   |
| Type           | `distributed-system` (single repo, two co-located processes, one public port)  |
| Language       | Python 3.10+ (FastAPI + uvicorn) backend + Next.js 16 / React 19 web           |
| Deploy Target  | `web/` as Next.js app, `server/` as a publicly reachable FastAPI service        |
| Owner          | Agora Conversational AI DevEx                                                  |
| Last Reviewed  | 2026-06-25                                                                     |
| Recipe Role    | `base`                                                                         |
| Recipe Version | `1.0.0`                                                                        |
| Recipe Status  | `experimental`                                                                 |

## L1 — Summaries

The Audience column helps agents prioritise: **Use** = consuming the recipe's behavior, **Maintain** = modifying internals.

| File                                     | Purpose                                                                           | Audience       |
| ---------------------------------------- | --------------------------------------------------------------------------------- | -------------- |
| [01_setup](L1/01_setup.md)               | bun + venv + pip setup, env vars (incl. required `CUSTOM_LLM_URL`), ngrok, commands | Use & Maintain |
| [02_architecture](L1/02_architecture.md) | Single-port topology, cascading STT→RAG LLM→TTS, retrieval pipeline              | Maintain       |
| [03_code_map](L1/03_code_map.md)         | `web/` and `server/` trees with key file responsibilities                         | Maintain       |
| [04_conventions](L1/04_conventions.md)   | Python async + FastAPI patterns, OpenAI SSE contract, Biome, JSON envelope        | Maintain       |
| [05_workflows](L1/05_workflows.md)       | Swap corpus, change STT/TTS, add routes, run locally, deploy                      | Use            |
| [06_interfaces](L1/06_interfaces.md)     | FastAPI route contracts, rewrites, env vars, LLM endpoint contract                | Use & Maintain |
| [07_gotchas](L1/07_gotchas.md)           | Public-URL requirement, single-process caveat, no localhost default, PORT in env  | Maintain       |
| [08_security](L1/08_security.md)         | Token007, co-public endpoint, `CUSTOM_LLM_API_KEY`, CORS, secret handling         | Maintain       |

## Recipe Profile

This repo declares `Recipe Role: base`. See [RECIPE.md](RECIPE.md) for extension points, invariants, and stable contracts before changing reusable surfaces.
