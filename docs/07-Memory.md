# Memory & State

| Field | Value |
|---|---|
| **Document** | Memory & state design |
| **Version** | v0.1 |
| **Related docs** | [07-Database-Schema](07-Database-Schema.md), [08-Phases](08-Phases.md) |

---

## 1. What state exists and where it lives

| Kind | Where | Notes |
|---|---|---|
| SQLite (`data.db`) | disk | segments, guide answers, quotes, themes, qa_log — the *source of truth* |
| FTS5 index | disk (in `data.db`) | derived from `segments`; rebuilt on ingest |
| LLM conversation | **stateless** | each Q&A is one-shot (evidence in → answer out); no chat history for safety |
| UI state | browser only | active tab, selected expert, search box — not persisted |
| ENV config | `.env` | `OPENAI_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL` (optional) |
| In-memory cache | process | (optional) evicted dict of recent `/ask` → answer (hash of question+evidence ids) |

## 2. Data lifecycle

```
first run        → schema init + seed guide_questions + ingest bundled transcripts
uploads          → add experts/transcripts/segments → rebuild FTS5 (incremental)
guide answers    → computed on demand, persisted; recomputed if source transcripts change
themes           → computed per request (tiny corpus, cheap) — optionally cached by transcript ids
qa_log           → appended per question (never mutated) — doubles as demo evidence + cache
```

## 3. Idempotency & re-runs

- **Startup ingest is idempotent:** same file name → upsert (replace) transcript + recompute answers.
- **Guide answers keyed** by `(question_id, transcript_id)` unique — safe to recompute anytime.
- **qa_log append-only** — leaving every demo question answered in the log is a feature (shows
  traceability), no cleanup needed.

## 4. Concurrency

- SQLite default (single connection, WAL optional). Enough for a local demo.
- FastAPI endpoints are async but sqlite3 calls are **synchronous & short**; we use a
  `threading.Lock` around the connection (or per-request connection) to avoid `table locked`.
- Scaling: swap to connection pool / Postgres later (see schema §6).

## 5. Prompt memory (context window)

- Evidence pack grows with `top_k`. For 3 transcripts × ~9 segments, full-corpus prompt is
  trivially small. Guard: cap evidence at `MAX_EVIDENCE_TOKENS ≈ 4000` per ask.

## 6. What we deliberately do NOT remember

- **No chat history** → every answer must stand on cited evidence (anti-drift / anti-hallucination).
- **No user accounts/profile** → out of scope.
- **No raw file blobs** after parse → segments are the canonical form (text re-derivable for quotes).