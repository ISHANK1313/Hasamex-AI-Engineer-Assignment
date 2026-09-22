# TRD — Technical Requirements Document

| Field | Value |
|---|---|
| **Document** | Technical Requirements Document |
| **Version** | v0.1 (Draft) |
| **Status** | Planning |
| **Related docs** | [01-PRD](01-PRD.md), [03-Architecture](03-Architecture.md), [05-Low-Level-Diagram](05-Low-Level-Diagram.md) |

---

## 1. System Requirements Summary

| # | Requirement | Detail |
|---|---|---|
| TR-1 | Ingest the 3 sample transcripts | Built-in sample files + optional file upload |
| TR-2 | Parse into structured segments | `{speaker, role, start_time_s, end_time_s, text}` |
| TR-3 | Guide-question → segment mapping | Deterministic scoring; 6 questions × 3 experts |
| TR-4 | Verbatim quote extraction | Exact substring of source text, char-range checked |
| TR-5 | Timestamps everywhere | Rendered as `MM:SS` from segment `start_time_s` |
| TR-6 | Themes & disagreements | Grouped cross-expert findings with quotes |
| TR-7 | Cross-transcript Q&A | Retrieval + (optional) LLM synthesis, always cited |
| TR-8 | Scaling design | Design supports 30+ transcripts without rework |

## 2. Recommended Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python 3.11+ | Fast to build, best AI ecosystem, easy to demo |
| Web framework | FastAPI + Uvicorn | Async, auto OpenAPI docs, lightweight |
| Frontend | Single-page app (vanilla JS + minimal CSS) | No build step, runs from the same server, "simple UI" per case |
| Storage | SQLite (via stdlib `sqlite3`) | Zero-install, file-based, easily migrates to Postgres later |
| LLM (optional) | OpenAI-compatible API (e.g., GPT-4o-mini) | Cheap, fast, strong at following citation instructions; adapter pattern allows swap |
| Embeddings (optional) | `text-embedding-3-small` or local `sentence-transformers` | Retrieval quality when Q&A used at scale |
| Vector search | `sqlite` FTS5 (BM25) baseline; Chroma/sqlite-vec for scale | No extra services for demo |
| Tests | `pytest` | Golden-dataset regression tests |
| Packaging | `requirements.txt` + `README` | Local run: `pip install -r requirements.txt` + `uvicorn app.main:app` |

> **Implementation note (v1 as shipped):** the module boundaries below were kept but collapsed into
> three files - `app/analyze.py` (parser + matching + quotes + themes + retrieval), `app/llm.py`
> (optional OpenAI-compatible call, prompts, citation check) and `app/main.py` (routes, in-memory
> store, error envelope). There is no SQLite, no FTS5 and no repository layer: the corpus is three
> transcripts held in memory. The schema in [07-Database-Schema](07-Database-Schema.md) is the design
> for 30+ transcripts, i.e. the answer to the scaling question, not the shape of v1. See
> [adr/0001](adr/0001-in-memory-store.md). Everything an optional model touches is still bounded by
> the evidence pack described below.

> **Note (Phase 0 decision):** the project folder hints the user may prefer **Java/Spring Boot**. The
> doc set is written so either stack can implement the same pipeline; final stack confirmed with user
> in Phase 0. The algorithms (below) are stack-agnostic.

## 3. Model Choice

### 3.1 Principle: Deterministic-first, LLM-last
- **Extraction, quote integrity, timestamps, and theme matching are done with code, not a model.**
  This guarantees 0 invented quotes and 100% traceability — the two hardest requirements.
- The LLM is used **only** for two soft tasks: (a) phrasing a guide answer as a short summary from
  retrieved evidence, (b) synthesising an answer in free-form Q&A. In both cases the model receives
  ONLY retrieved transcript segments and is instructed to cite them.

### 3.2 Chosen model (when key present)
- **GPT-4o-mini** (or any OpenAI-compatible `chat/completions` endpoint):
  - Cheap + fast; sufficient quality for summarisation over small contexts.
  - Strong instruction-following for "answer only from the given evidence".
- **Embeddings:** `text-embedding-3-small` for retrieval; falls back to FTS5/BM25 with no key.
- **No-key mode:** all Must features (FR-1..FR-8, FR-11) work with lexical retrieval only — the app
  shows snippets verbatim instead of LLM prose.

### 3.3 Why not a bigger/agentic setup
- Overkill for 6 questions × 3 short transcripts; a multi-agent loop risks hallucination and slow demo.

## 4. Core Algorithms

### 4.1 Transcript parser
1. Split file into header + dialogue lines.
2. Header parse: expert name, role, market (regex: `Expert N – Name`, `Role:`, `Market:`).
3. Dialogue lines match `^(\d{2}):(\d{2})\s+([^:]+):\s*(.*)$` → `start_time_s`, speaker, text.
4. `end_time_s` = next segment's start (or `start + estimated 18s` for the last).
5. Emit structured segments; detect anomalies (missing timestamps, empty speakers) with clear errors.

### 4.2 Guide-question matcher (deterministic)
- Build a per-question **keyword/semantic lexicon** from the guide question (e.g., Q3 → `budget`, `roi`,
  `cost`, `pay for itself`, `total cost of ownership`, `capital`).
- For each segment, score = weighted keyword hits + substring overlaps with question terms.
- Take the top-1 (or top-2) segments per expert per question; require a minimum score or mark **"Not covered"**.
- Store the mapping as golden data (see Reference §4) and assert it in tests.

### 4.3 Quote extractor
- A **quote** must be an exact substring of one segment's text (`text.find(quote) >= 0`).
- Extract sentence-length spans around match scores; strip padding whitespace/punctuation.
- Store `start_char/end_char` + segment id for integrity checks. **No LLM in this path.**
- UI shows quote with `[MM:SS]` from the segment.

### 4.4 Theme & disagreement analyser
- Group segments by topic clusters using a small topic lexicon (adoption, cost/ROI, training,
  outcomes, timeline, growth/outlook).
- For each topic with ≥2 experts present → **theme** (with per-expert quotes).
- For topics where experts express contrasting stances (polarity lexicon + numeric comparisons,
  e.g. growth %, timeline months) → **disagreement** with labelled sides.
- Golden dataset (Reference §5) asserts expected outputs.

### 4.5 Q&A engine (hybrid)
1. Tokenise + query expansion (synonyms table).
2. Rank segments: FTS5/BM25 score (+ optional embedding cosine, when key available).
3. Top-k (k=4) segments → context block (with speaker, timestamp, verbatim text).
4. If LLM key: prompt = **system: "Answer ONLY from the evidence. Cite [MM:SS, Speaker] after each claim. If evidence is insufficient say so."** + evidence block.
5. If no key: return the top segments verbatim + a short highlight (exact quoted sentences) — still fully cited.

### 4.6 Hallucination controls (summary)
| Control | Mechanism |
|---|---|
| Verbatim quotes | Exact-substring check; LLM never writes quotes |
| Citation anchoring | LLM output post-checked: any bracketed timestamp must exist in the evidence block |
| "I don't know" policy | If top score below threshold → explicit "insufficient evidence" + nearest snippets |
| Low temperature | `temperature=0.2` for synthesis |
| No-key fallback | Deterministic path used in demo if panel environment has no key |
| Regression tests | Golden dataset asserts every answer/quote exists in source |

## 5. Data Model (see [07-Database-Schema](07-Database-Schema.md))

`experts, transcripts, segments, guide_questions, guide_answers, quotes, themes, theme_items, qa_log`

## 6. API Contract (v1)

Base path: `/api`

| Method | Path | Purpose | Request | Response (abridged) |
|---|---|---|---|---|
| GET | `/health` | Liveness | — | `{"status":"ok"}` |
| POST | `/transcripts/ingest` | Load samples or upload files | `files` (optional) | `{"ingested": [{"expert": "...", "segments": 9}]}` |
| GET | `/transcripts` | List loaded transcripts | — | `[{"id","expert","market","segments"}]` |
| GET | `/guide-answers` | All guide answers (per expert) | — | `{questions: [{id, text, answers: [{expert, summary, confidence, quotes: [{text, timestamp, segment_id}]}]}]}` |
| GET | `/themes` | Themes + disagreements | — | `{themes: [...], disagreements: [...]}` |
| POST | `/ask` | Cross-transcript Q&A | `{"question": "..."}` | `{answer, citations: [{speaker, timestamp, text, transcript}]}` |

Example `POST /api/ask`:
```json
{
  "question": "How long does buying a robotic system typically take?",
  "top_k": 4,
  "use_llm": true
}
```
Response shape:
```json
{
  "answer": "Purchase timelines range from six to eighteen months... [06:08, Dr. Jean Martin]",
  "citations": [
    {"speaker": "Dr. Jean Martin", "timestamp": "06:08", "text": "Six to twelve months is realistic...", "transcript": "France"}
  ]
}
```

## 7. Error Handling & Logging

- Parse failures → 422 with `{line_no, reason}`.
- Missing transcript → 404.
- No `.env`/API key → LLM features degrade gracefully (log once) — API never errors because of it.
- LLM timeout (5s) → fallback to lexical answer with notice.
- Structured `logging` per service; `qa_log` table stores every question/answer for demo evidence.

## 8. Security & Config

- API key in `.env` (gitignored); `.env.example` committed.
- CORS limited to localhost for demo.
- No PII in transcripts (all fictional sample data).
- Input size guard on upload (e.g., ≤ 2 MB) to avoid abuse.

## 9. Testing Strategy

| Level | Covers | Example |
|---|---|---|
| Unit — parser | header + timestamp regex | 9 segments parsed per sample transcript |
| Unit — matcher | Q↔segment mapping | Q3 → Germany segment for Anna Keller at `02:08` |
| Unit — quotes | verbatim integrity | every quote passes `source.contains(quote)` |
| Golden dataset | all 18 guide answers | assert expected quote timestamps (Reference §4) |
| Golden dataset | themes/disagreements | Reference §5 items present |
| Integration | full API flows | ingest → guide-answers → themes → ask |
| No-key mode | degradation | `/ask` returns cited snippets without LLM |

## 10. Scaling: 3 → 30+ Transcripts

- **Ingestion** stays the same; per-transcript processing is parallelisable (worker pool / async).
- **Indexing:** SQLite FTS5 → optional vector index (Chroma / sqlite-vec); incremental re-index on ingest.
- **Retrieval:** BM25 + embedding hybrid; k changes with corpus size; optional reranking (Cohere/cross-encoder).
- **Themes at scale:** topic clustering (embeddings + HDBSCAN) instead of lexicon; same quote citation layer.
- **Cost:** batch embeddings; cache LLM answers (qa_log); evict stale sessions.
- **Architecture impact:** none — services already separated (see [03-Architecture](03-Architecture.md) §3);
  storage can swap SQLite → Postgres/pgvector behind a repository interface.