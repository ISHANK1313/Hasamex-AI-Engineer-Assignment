# Architecture Document

| Field | Value |
|---|---|
| **Document** | System Architecture |
| **Version** | v0.1 (Draft) |
| **Status** | Planning |
| **Related docs** | [04-High-Level-Diagram](04-High-Level-Diagram.md), [05-Low-Level-Diagram](05-Low-Level-Diagram.md), [06-Request-Flow](06-Request-Flow.md) |

---

## 1. Architecture Goals

1. **Traceability by construction** — every answer/quote carries a segment + timestamp because the
   pipeline keeps source references through every layer.
2. **Deterministic core, optional AI** — all "must" features work without an LLM; the LLM only polishes
   text over retrieved, cited evidence. This is the main hallucination defence and the main demo safety.
3. **Simple to demo** — one process serves a single-page UI and the API. Two commands to run.
4. **Scalable shape** — layering matches how a 30+ transcript system would look, so the demo story
   ("how would you scale?") is honest.

## 1a. Implementation note (v1 as shipped)

The layered shape below is what ships, at the scale of one small process:

| Doc layer | Shipped as |
|---|---|
| `app/ingest/` + `app/services/` | `app/analyze.py` (parser, turn pairing, matcher, quotes, themes, lexical retrieval) |
| `app/llm/` | `app/llm.py` (one `httpx.post` to any OpenAI-compatible endpoint, prompts, citation post-check) |
| `app/api/` + `app/storage/` | `app/main.py` (6 routes, in-memory store, `{error:{code,message}}` envelope) |
| `static/` | `static/index.html` + `app.js` + `style.css`, served by the same process |

No database, no FTS5, no repository interface and no dependency injection: the corpus is three
transcripts held in memory, so those layers would be scaffolding for a scale the app does not have
([adr/0001](adr/0001-in-memory-store.md)). The SQLite/FTS5 design in
[07-Database-Schema](07-Database-Schema.md) stays as the concrete 30+ transcript answer. The
deterministic-core / optional-model split in §5 (D1, D2, D4) is implemented exactly as described.

## 2. High-Level View

```
┌──────────────────────────┐        ┌──────────────────────────────────────────────┐
│   Browser (SPA)          │        │              Backend (FastAPI)                │
│  - Guide answers view    │  HTTP  │                                              │
│  - Themes view           │◄──────►│  api/  ─►  services/  ─►  storage/            │
│  - Q&A view              │  JSON  │  routes    │        │    │  sqlite3  ── data.db│
│  - Upload                │        │            │        │    │  FTS5 index         │
└──────────────────────────┘        │            │        │    └─────────────────────┘
                                    │            │        └── llm/ (optional)        │
                                    │            │            └─ OpenAI-compatible    │
                                    │            └─ ingest/ (parser)                 │
                                    └──────────────────────────────────────────────┘
```

## 3. Layer Responsibilities

| Layer | Module | Responsibility |
|---|---|---|
| **Web** | `app/api/` | Route handlers, request validation, JSON serialisation |
| **Application services** | `app/services/` | Orchestration: guide answers, themes, Q&A, quotes |
| **Domain/ingestion** | `app/ingest/` | Transcript parser, segment model, header extraction |
| **AI (optional)** | `app/llm/` | Thin adapter to any OpenAI-compatible endpoint; prompt factory; citation post-check |
| **Storage** | `app/storage/` | Repository over SQLite (schema in 07); FTS5 index; `qa_log` |
| **Frontend** | `static/` | One `index.html` + `app.js` + `style.css`, served by FastAPI |

## 4. Component Diagrams (per concern)

### 4.1 Ingestion & parsing

```
transcript file (text)
   │
   ▼
[ HeaderParser ] ─► {expert, role, market}
[ LineParser   ] ─► {segment_id, speaker, start_time_s, end_time_s, text}
   │
   ▼
[ Validator ] ── errors? ──► 422 {line_no, reason}
   │
   ▼
[ SegmentRepository.save ] ──► SQLite (transcripts, segments)
```

### 4.2 Guide answers

```
guide questions (seed)                    segments (by expert)
      │                                        │
      ▼                                        ▼
   [ QuestionMatcher: score(segment, question) ]
      │ top-1/top-2 per expert per question
      ▼
   [ QuoteExtractor: exact substring, char range ]
      │
      ▼
   [ (optional) LLM summariser over cited evidence ]
      │
      ▼
   guide_answers rows + quotes rows ──► /api/guide-answers
```

### 4.3 Themes & disagreements

```
all segments (all experts)
   │
   ▼
[ TopicClusteredLexicon ] ──► topic buckets {topic, [segments]}
   │  groups by ≥2 experts → THEME
   │  contrasting stances  → DISAGREEMENT
   ▼
[ ThemeFormula ] ──► themes + theme_items rows ──► /api/themes
```

### 4.4 Q&A

```
question
   │
   ▼
[ Retrieval: FTS5/BM25 (+ embeddings if key) ] ──► top-k segments
   │
   ▼
[ Evidence pack: {speaker, timestamp, verbatim text} ]
   │
   ├─ no LLM ──► verbatim snippets + highlights (fully cited) ──► /api/ask
   │
   └─ LLM ──► [ Prompt factory ] ─► [ LLM gateway ] ─► [ Citation post-check ]
                                        │ fails? ──► fallback to lexical verbatim
                                        ▼
                                   answer + citations ──► /api/ask
```

## 5. Key Design Decisions & Trade-offs

| # | Decision | Why | Trade-off |
|---|---|---|---|
| D1 | Deterministic parsing/matching first, LLM last | Guarantees 0 invented quotes; deterministic demo | Less "fancy" than pure LLM; answer summaries are simple in no-key mode |
| D2 | Exact-substring quote integrity | Hard requirement: traceable answers; cheap test | Quotes look verbatim (by design — the case explicitly wants exact quotes) |
| D3 | SQLite + FTS5 baseline | Zero-install, offline demo; honest baseline | Not a distributed datastore → documented swap path (Postgres/pgvector) |
| D4 | No-key fallback | Panel may not have an API key; app must still work | No generative summaries without key |
| D5 | SPA served by the API server | One process, no CORS/build tooling | Not a separate deployable frontend |
| D6 | LLM adapter interface | Swap models (GPT, Claude, local) without touching services | One more abstraction |
| D7 | Golden dataset regression tests | "Accuracy" is a core evaluation axis; tests make it checkable | Tests must be maintained when transcripts change |

## 6. What the Demo Video Should Show (architecture story)

1. Transcript → parsed segments with timestamps (deterministic, testable).
2. Guide answer rendering: summary + exact quotes + `[MM:SS]` next to each.
3. Themes & disagreements surfaced from the same source segments.
4. Q&A: question in → answer with citations → link back to segment.
5. The three hallucination controls (verbatim quotes, citation anchoring, "insufficient evidence").
6. Scaling story: same layers, index + clustering + parallel ingestion for 30+ transcripts.

## 7. Scaling (from case demo requirement)

```
3 transcripts                        30+ transcripts
─────────────────                    ─────────────────────────────
SQLite + FTS5 (BM25)                 + vector index (sqlite-vec/Chroma) + hybrid retrieval
lexicon topic clustering             embedding clustering (HDBSCAN)
sequential ingest                    parallel ingest (worker pool)
LLM per shift per call (cached)      batch embeddings + answer cache (qa_log)
single process                       read replicas / async workers (same code path)
```