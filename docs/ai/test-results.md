# Docs Test Results

**Date:** 2026-06-25
**Repo:** `AgoraIO-Conversational-AI/recipe-agent-rag`
**Branch:** `docs/progressive-disclosure`

---

## Structural Checks

| Check | Result |
| ----- | ------ |
| `L0_repo_card.md` exists | Pass |
| `L0_repo_card.md` ≤ 50 lines (actual: 36) | Pass |
| `L0_repo_card.md` has all Identity fields | Pass |
| `L0_repo_card.md` has L1 index table | Pass |
| `L1/01_setup.md` exists | Pass |
| `L1/02_architecture.md` exists | Pass |
| `L1/03_code_map.md` exists | Pass |
| `L1/04_conventions.md` exists | Pass |
| `L1/05_workflows.md` exists | Pass |
| `L1/06_interfaces.md` exists | Pass |
| `L1/07_gotchas.md` exists | Pass |
| `L1/08_security.md` exists | Pass |
| `L1/L2/_index.md` exists | Pass |
| `L1/L2/retrieval_pipeline.md` exists | Pass |
| `L1/L2/session_lifecycle.md` exists | Pass |
| `RECIPE.md` exists with YAML frontmatter | Pass |
| `AGENTS.md` has `## How to Load` section | Pass |
| `AGENTS.md` has `## Git Conventions` section | Pass |
| `AGENTS.md` has `## Doc Commands` section | Pass |
| `AGENTS.md` declares `Recipe Role: base` | Pass |
| Stale "docs/ai not present" note removed | Pass |

**Structural: 21/21 Pass**

---

## Relative Link Check

All markdown links in `docs/ai/` were resolved relative to their source file.

| Metric | Value |
| ------ | ----- |
| Total links checked | 28 |
| Broken links | 0 |

**Link check: Pass (28/28)**

---

## pytest — Backend Tests

Executed in throwaway venv `/tmp/v_rag` (Python 3.14.4, pytest 9.1.1).
Install: `pip install -r requirements.txt -r requirements-dev.txt`

```
platform darwin -- Python 3.14.4, pytest-9.1.1
collected 12 items

tests/test_agent_construction.py::test_start_constructs_real_agent_and_returns_shape PASSED
tests/test_llm.py::test_health PASSED
tests/test_llm.py::test_streaming_sse_contract PASSED
tests/test_llm.py::test_non_streaming_rejected PASSED
tests/test_llm_mount.py::test_llm_health_is_mounted_under_slash_llm PASSED
tests/test_llm_mount.py::test_llm_chat_completions_reachable_through_mount PASSED
tests/test_llm_mount.py::test_llm_module_has_no_agora_dependency PASSED
tests/test_rag.py::test_retrieve_hit PASSED
tests/test_rag.py::test_retrieve_miss PASSED
tests/test_rag.py::test_run_agent_turn_grounds_answer PASSED
tests/test_rag.py::test_run_agent_turn_miss PASSED
tests/test_rag.py::test_retrieve_no_false_positive_on_substring PASSED

12 passed, 1 warning in 2.48s
```

Note: 1 warning — `httpx` deprecation in `starlette.testclient`; not a test failure.
Venv removed after run.

**pytest: 12/12 Pass**

---

## Q&A — Docs Accuracy Verification

Each question was answered from the docs, then verified against source code.

### Category 1: Identity and Setup (3 questions)

| # | Question | Answer from Docs | Source Verified | Result |
|---|----------|-----------------|-----------------|--------|
| 1 | What language and framework does the backend use? | Python 3.10+ / FastAPI (L0, 01_setup) | `server/requirements.txt`: `fastapi>=0.100.0`; `server/src/server.py`: `from fastapi import ...` | Pass |
| 2 | What is the `CUSTOM_LLM_URL` default? | No default — validated at startup; must be public (01_setup, 07_gotchas) | `server/src/agent.py`: `if not self.custom_llm_url: raise ValueError(...)` — no default assigned | Pass |
| 3 | What does `bun run setup` do? | Installs web deps + creates `server/venv` from `requirements.txt`; copies `.env.example` → `.env.local` if missing (01_setup) | `package.json` `setup` script: `setup:env && setup:server && setup:web && setup:done` | Pass |

### Category 2: Architecture (3 questions)

| # | Question | Answer from Docs | Source Verified | Result |
|---|----------|-----------------|-----------------|--------|
| 4 | Who calls `/llm/chat/completions` — the browser or Agora cloud? | Agora cloud calls it directly; the browser never calls `/llm/*` (02_architecture, 06_interfaces) | `ARCHITECTURE.md`: `POST <CUSTOM_LLM_URL>/chat/completions` path is from Agora ConvoAI Cloud to `/llm` | Pass |
| 5 | How is the `/llm` endpoint mounted into the server? | `app.mount("/llm", llm_app)` in `server/src/server.py` (02_architecture) | `server/src/server.py` line 198: `app.mount("/llm", llm_app)` | Pass |
| 6 | What STT and TTS vendors are used? | Deepgram STT nova-3; MiniMax TTS speech_2_6_turbo (02_architecture, 06_interfaces) | `server/src/agent.py`: `DeepgramSTT(model="nova-3")`, `MiniMaxTTS(model="speech_2_6_turbo", ...)` | Pass |

### Category 3: Retrieval Pipeline (3 questions)

| # | Question | Answer from Docs | Source Verified | Result |
|---|----------|-----------------|-----------------|--------|
| 7 | What does `retrieve()` return on a miss? | An empty list `[]` (retrieval_pipeline, test_rag.py) | `server/src/llm.py`: `return [(topic, doc) for _, topic, doc in scored[:top_k]]` — returns `[]` when no topics score > 0 | Pass |
| 8 | What does `run_agent_turn()` return when no docs match? | `"I don't have anything on that yet. You can ask about: <topic list>."` (retrieval_pipeline) | `server/src/llm.py` `run_agent_turn()`: `return f"I don't have anything on that yet. You can ask about: {topics}."` | Pass |
| 9 | How is `TOP_K` set? | Read from `RAG_TOP_K` env var at module load; defaults to `1`; guarded against non-integer values (01_setup, retrieval_pipeline) | `server/src/llm.py`: `TOP_K = max(1, int(os.getenv("RAG_TOP_K", "1")))` inside try/except | Pass |

### Category 4: Interfaces and Contracts (2 questions)

| # | Question | Answer from Docs | Source Verified | Result |
|---|----------|-----------------|-----------------|--------|
| 10 | What is the success response envelope? | `{ "code": 0, "msg": "success", "data": { } }` (04_conventions, 06_interfaces) | `server/src/server.py` routes: `return {"code": 0, "msg": "success", "data": result}` | Pass |
| 11 | What does the browser API client's `startAgent()` send? | `POST /api/startAgent` with `{ channelName, rtcUid, userUid }` (06_interfaces) | `web/src/services/api.ts`: `body: JSON.stringify({ channelName, rtcUid, userUid })` | Pass |

### Category 5: Gotchas and Security (3 questions)

| # | Question | Answer from Docs | Source Verified | Result |
|---|----------|-----------------|-----------------|--------|
| 12 | Why must `llm.py` not import `agora-agents`? | It is provider-agnostic so it can be extracted to a dedicated service; `test_llm_mount.py` enforces this via AST inspection (07_gotchas, RECIPE.md invariants) | `server/tests/test_llm_mount.py`: `test_llm_module_has_no_agora_dependency` uses `ast.parse` + `ast.walk` | Pass |
| 13 | Where do `AGORA_APP_CERTIFICATE` and `CUSTOM_LLM_URL` live? | Server-only in `server/.env.local`; never reach the browser (08_security) | `server/src/agent.py`: reads both from `os.getenv`; never returned to browser; `server/.env.local` is gitignored | Pass |
| 14 | What env var must NOT be put in `server/.env.example`? | `PORT` — `verify:local:fastapi` injects a random `PORT` via `load_dotenv(override=True)` (07_gotchas) | `server/src/server.py`: `port = int(os.getenv("PORT", "8000"))` at boot; `server/.env.example` has no `PORT` line | Pass |

---

## Summary Table by Category

| Category | Questions | Pass | Fail |
| -------- | --------- | ---- | ---- |
| Identity and Setup | 3 | 3 | 0 |
| Architecture | 3 | 3 | 0 |
| Retrieval Pipeline | 3 | 3 | 0 |
| Interfaces and Contracts | 2 | 2 | 0 |
| Gotchas and Security | 3 | 3 | 0 |
| **Total** | **14** | **14** | **0** |

---

## Fix / Retest Log

No issues found. All structural checks, link checks, pytest, and Q&A passed on the first run.

---

## Overall Result

| Suite | Pass | Total |
| ----- | ---- | ----- |
| Structural checks | 21 | 21 |
| Relative link check | 28 links | 0 broken |
| pytest backend | 12 | 12 |
| Q&A accuracy | 14 | 14 |
| **Grand total** | **75** | **75** |
