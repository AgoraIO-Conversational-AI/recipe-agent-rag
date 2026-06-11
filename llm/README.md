# RAG LLM Endpoint — Mock

An OpenAI-compatible `POST /chat/completions` server (port 8001) that Agora cloud
calls during a conversation. On each user query this endpoint retrieves the
best-matching document from a small in-code corpus and returns a grounded reply
("Based on our docs: …"), so you can exercise the full STT → RAG LLM → TTS
pipeline with **no LLM API key**.

It has no `agora-agents` dependency — it is a plain FastAPI app, which is exactly
the boundary you replace with your own RAG pipeline.

## How it works

```
user query
  │
  ▼  retrieve(query)
  │  score each CORPUS topic by word overlap with query
  │  return top-K (topic, doc) pairs
  ▼
  if hits:  "Based on our docs: <doc snippets>"
  if miss:  "I don't have anything on that yet. You can ask about …"
```

`CORPUS` is a plain Python dict in `src/custom_llm_server.py`. `retrieve()` is real
keyword-scoring code. The generation step is mocked (no LLM API calls). Tests live
in `tests/test_rag.py`.

## The contract

Implement `POST /chat/completions` returning OpenAI-style SSE:

- first chunk sets `delta.role = "assistant"`
- content chunks carry `delta.content`
- a final chunk sets `finish_reason = "stop"`
- the stream terminates with `data: [DONE]`

Only streaming (`stream: true`) is supported; non-streaming requests return 400.

## Run

```bash
cd llm
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python src/custom_llm_server.py     # serves on CUSTOM_LLM_PORT (default 8001)
```

## Expose it publicly

Agora cloud — not the browser — calls this server, so it must be reachable from
the public internet. For local dev, tunnel it:

```bash
ngrok http 8001
```

Then set `CUSTOM_LLM_URL=https://<tunnel>/chat/completions` in `server/.env.local`.

## Auth

This mock does **not** authenticate. A production endpoint should validate the
`Authorization: Bearer <CUSTOM_LLM_API_KEY>` header that Agora cloud forwards
(the key you set on the agent backend).

## Replacing the mock

Swap `CORPUS` and `retrieve()` in `src/custom_llm_server.py` for a real vector
store (e.g. ChromaDB, pgvector, Pinecone). Keep `run_agent_turn()` and the OpenAI
streaming contract unchanged. Adjust `RAG_TOP_K` in `llm/.env.local` to control
how many docs are retrieved per query (default `1`).

## Environment

| Variable | Default | Notes |
| --- | --- | --- |
| `CUSTOM_LLM_PORT` | `8001` | Listening port |
| `RAG_TOP_K` | `1` | Number of corpus docs to retrieve per query |
