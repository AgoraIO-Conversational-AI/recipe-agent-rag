**When to Read This:** Changing the retrieval logic, swapping the in-code corpus for a real vector store, debugging the `/llm/chat/completions` endpoint, or understanding the OpenAI SSE streaming contract that Agora cloud expects.

# Retrieval Pipeline

> The RAG LLM endpoint in `server/src/llm.py`. Retrieval is real keyword-scored code; generation is mocked (zero-key). Replace `CORPUS` and `retrieve()` to adopt a real vector store. The HTTP streaming contract must not change.

## Corpus and retrieval

`CORPUS` is a plain Python dict mapping topic strings to document text:

```python
CORPUS = {
    "refund policy": "Refunds are available within 30 days of purchase with your receipt.",
    "business hours": "We are open Monday to Friday, 9 a.m. to 6 p.m.",
    "shipping":       "Standard shipping takes three to five business days.",
    "warranty":       "Every product includes a one-year limited warranty.",
}
```

`retrieve(query, corpus, top_k)` tokenizes the query with `re.findall(r"[a-z0-9]+", ...)`, scores each topic by counting matching tokens, and returns the top-K `(topic, doc)` pairs sorted by score descending. A topic with zero score is excluded.

`TOP_K` is read from `RAG_TOP_K` env var at module load; guarded against non-integer values (defaults to `1`).

## Generation

`_extract_last_user_text(messages)` walks the message list in reverse to find the last user message and extracts plain text from it (handles `str`, `List[TextContent]`, and `List[dict]` shapes).

`run_agent_turn(messages)` calls `retrieve()` on the last user text:

- **Hit:** `"Based on our docs: <snippet1> <snippet2>"`
- **Miss:** `"I don't have anything on that yet. You can ask about: <topic list>."`

## OpenAI SSE streaming contract

Agora ConvoAI requires `stream: true`. The endpoint rejects `stream: false` with 400.

Stream shape (in order):

1. **Role chunk** — `delta: { role: "assistant", content: "" }`, `finish_reason: null`
2. **Content chunks** — one per word; `delta: { content: "<token>" }`, `finish_reason: null`; 50 ms delay between words to simulate token generation.
3. **Stop chunk** — `delta: { content: "" }`, `finish_reason: "stop"`
4. **Done sentinel** — `data: [DONE]`

Each chunk JSON shape:

```json
{
  "id": "chatcmpl-<hex>",
  "object": "chat.completion.chunk",
  "created": <unix-timestamp>,
  "model": "<model>",
  "choices": [{ "index": 0, "delta": {...}, "finish_reason": null }]
}
```

## Env-loading order in `llm.py`

`llm.py` loads `.env.local` then `.env` with `override=False`. This means an explicitly exported environment variable (such as `CUSTOM_LLM_PORT` injected by `verify:local:llm`) takes precedence over the file values. In `server.py` the same files are loaded with `override=True` so the file always wins for the main server.

## Replacing the mock

1. Replace `CORPUS` and `retrieve()` with your vector store client (e.g., ChromaDB, pgvector, Pinecone).
2. Keep `run_agent_turn()` signature and return type unchanged (`str`).
3. Keep the HTTP contract: `POST /chat/completions` accepting `ChatCompletionRequest`, returning `StreamingResponse` SSE.
4. Add new env vars (e.g., `VECTOR_DB_URL`) to `server/.env.example`.
5. In production, validate the `Authorization: Bearer` header before processing.
6. Run `cd server && pytest tests -v` — update `test_rag.py` to match the new corpus.

## Mount and isolation

`server/src/llm.py` is mounted into the FastAPI app via:

```python
app.mount("/llm", llm_app)
```

`test_llm_mount.py` verifies that `llm.py` imports no Agora SDK packages via AST inspection. Keep `llm.py` free of `agora-agents` so it can be extracted to a standalone service without dependency changes.

## Related

- [06_interfaces](../06_interfaces.md) — full `/llm/chat/completions` route contract.
- [07_gotchas](../07_gotchas.md) — public URL requirement and env-loading pattern.
