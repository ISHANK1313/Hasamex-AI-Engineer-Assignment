# Database Schema

| Field | Value |
|---|---|
| **Document** | Database Schema |
| **Version** | v0.1 |
| **Engine** | SQLite (stdlib `sqlite3`); FTS5 virtual table for full-text search |
| **Related docs** | [02-TRD](02-TRD.md), [05-Low-Level-Diagram](05-Low-Level-Diagram.md) |

> **Why SQLite:** zero-install, single-file `data.db`, perfect for a local demo. The schema is
> deliberately simple so it maps 1:1 to Postgres/pgvector when scaling (documented swap path).
>
> **Implementation note (v1 as shipped):** this schema is **not** implemented in v1. The shipped app
> holds the three transcripts in memory and has no database, no FTS5 index and no repository layer
> (see [adr/0001](adr/0001-in-memory-store.md)). The tables below are kept because they are the
> concrete answer to "how would you scale 3 transcripts to 30+", and because the analysis layer is
> already written around them: `load_transcripts` becomes the `segments` read, `lexical_search`
> becomes the FTS5 BM25 query in §3, and guide answers, quotes and themes map onto `guide_answers`,
> `quotes` and `themes`/`theme_items` as designed. Two v1 differences to be aware of: `qa_log` is not
> persisted (nothing is logged), and the `experts` table is replaced by the header block parsed from
> each file.

---

## 1. ER Diagram (Mermaid)

```mermaid
erDiagram
    EXPERTS ||--o{ TRANSCRIPTS : "speaks in"
    TRANSCRIPTS ||--o{ SEGMENTS : "contains"
    GUIDE_QUESTIONS ||--o{ GUIDE_ANSWERS : "answered by"
    EXPERTS ||--o{ GUIDE_ANSWERS : "gives"
    GUIDE_ANSWERS ||--o{ QUOTES : "supported by"
    SEGMENTS ||--o{ QUOTES : "source of"
    THEMES ||--o{ THEME_ITEMS : "groups"
    THEME_ITEMS ||--o{ QUOTES : "cites"
    QA_LOG ||--o{ QA_CITATIONS : "uses"

    EXPERTS { int id PK, text name, text role, text market, text transcript_file }
    TRANSCRIPTS { int id PK, int expert_id FK, text source_file, text raw_header }
    SEGMENTS { int id PK, int transcript_id FK, text speaker, int start_time_s,
               int end_time_s, text text }
    GUIDE_QUESTIONS { int id PK, int q_number, text question_text, text topic }
    GUIDE_ANSWERS { int id PK, int question_id FK, int transcript_id FK,
                    text summary, real confidence, int not_covered }
    QUOTES { int id PK, int answer_id FK, int segment_id FK, int theme_item_id FK NULL,
             text text, int start_char, int end_char }
    THEMES { int id PK, text topic, text kind }          -- kind = theme|disagreement
    THEME_ITEMS { int id PK, int theme_id FK, text label, text stance }
    QA_LOG { int id PK, text question, text answer, text provider, text created_at }
    QA_CITATIONS { int id PK, int qa_log_id FK, int segment_id FK }
```

## 2. DDL (SQLite reference)

```sql
-- core
CREATE TABLE experts (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,          -- "Dr. Jean Martin"
    role            TEXT,                   -- "Head of Urology"
    market          TEXT,                   -- "France"
    transcript_file TEXT UNIQUE             -- "Transcript_1_France.txt"
);

CREATE TABLE transcripts (
    id          INTEGER PRIMARY KEY,
    expert_id   INTEGER NOT NULL REFERENCES experts(id),
    source_file TEXT NOT NULL,
    raw_header  TEXT
);

CREATE TABLE segments (
    id            INTEGER PRIMARY KEY,
    transcript_id INTEGER NOT NULL REFERENCES transcripts(id),
    speaker       TEXT NOT NULL,            -- interviewer or expert name
    start_time_s  INTEGER NOT NULL,         -- seconds, from MM:SS
    end_time_s    INTEGER NOT NULL,         -- next segment start / start+18 for last
    text          TEXT NOT NULL
);
CREATE INDEX idx_segments_transcript ON segments(transcript_id);

-- guide
CREATE TABLE guide_questions (
    id            INTEGER PRIMARY KEY,
    q_number      INTEGER NOT NULL,         -- 1..6
    question_text TEXT NOT NULL,
    topic         TEXT                      -- adoption|cost-roi|training|outcomes|timeline|growth
);
CREATE TABLE guide_answers (
    id            INTEGER PRIMARY KEY,
    question_id   INTEGER NOT NULL REFERENCES guide_questions(id),
    transcript_id INTEGER NOT NULL REFERENCES transcripts(id),
    summary       TEXT,
    confidence    REAL,                     -- matcher score (0..1); -1 if not_covered
    not_covered   INTEGER DEFAULT 0
);
CREATE UNIQUE INDEX uq_answer ON guide_answers(question_id, transcript_id);

CREATE TABLE quotes (
    id          INTEGER PRIMARY KEY,
    answer_id   INTEGER REFERENCES guide_answers(id),   -- NULL for theme/qa quotes
    theme_item_id INTEGER REFERENCES theme_items(id),   -- NULL for answer quotes
    segment_id  INTEGER NOT NULL REFERENCES segments(id),
    text        TEXT NOT NULL,              -- EXACT verbatim substring
    start_char  INTEGER NOT NULL,           -- position within segment.text
    end_char    INTEGER NOT NULL            -- integrity check: segment.text[start:end] == text
);
CREATE INDEX idx_quotes_segment ON quotes(segment_id);

-- themes / disagreements
CREATE TABLE themes (
    id   INTEGER PRIMARY KEY,
    topic TEXT NOT NULL,
    kind  TEXT NOT NULL CHECK (kind IN ('theme','disagreement'))
);
CREATE TABLE theme_items (
    id        INTEGER PRIMARY KEY,
    theme_id  INTEGER NOT NULL REFERENCES themes(id),
    label     TEXT,                         -- e.g. "Growth: FR expects 15-20%/yr"
    stance    TEXT                          -- 'agree' | 'a' | 'b' for disagreements
);

-- Q&A log (also our answer cache for demos)
CREATE TABLE qa_log (
    id         INTEGER PRIMARY KEY,
    question   TEXT NOT NULL,
    answer     TEXT NOT NULL,
    provider   TEXT NOT NULL CHECK (provider IN ('lexical','openai','fallback')),
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE qa_citations (
    id         INTEGER PRIMARY KEY,
    qa_log_id  INTEGER NOT NULL REFERENCES qa_log(id),
    segment_id INTEGER NOT NULL REFERENCES segments(id)
);
```

## 3. FTS5 Full-Text Index

```sql
CREATE VIRTUAL TABLE fts_segments USING fts5(
    text,
    speaker,
    transcript_id UNINDEXED,
    segment_id UNINDEXED
);
-- rebuild after ingest:
INSERT INTO fts_segments(rowid, text, speaker, transcript_id, segment_id)
SELECT id, text, speaker, transcript_id, id FROM segments;
```
Query (BM25): `SELECT * FROM fts_segments WHERE fts_segments MATCH ? ORDER BY rank LIMIT 4`

> **Escaping note:** user question must be tokenised/escaped before `MATCH` (FTS5 syntax chars:
> `AND OR NOT " ( ) * : -`). We pass raw question words joined by `AND`, quoted per token.

## 4. Constraints & integrity rules

- `quotes.text` **must** equal `segments.text[start_char:end_char]` — enforced by the app layer and
  asserted by tests (this is the anti-hallucination contract).
- `guide_answers.not_covered=1` ⇔ `summary IS NULL`.
- `qa_citations.segment_id` always populated — Q&A answers are never citation-free.
- One `experts.transcript_file` per expert (samples replace the built-in on same-name upload).

## 5. Seed data

| Table | Content |
|---|---|
| `experts` | 3 rows (France / Germany / UK) — parsed from bundled files at startup |
| `guide_questions` | 6 rows, numbers 1–6, text + topic |
| everything else | computed at ingest time; persisted for reuse + qa_log |

## 6. Scaling path

| Now (SQLite) | Later (30+ transcripts) |
|---|---|
| file `data.db` | Postgres 16 (+ pgvector column) |
| FTS5 BM25 | hybrid BM25 + embeddings; optional cross-encoder rerank |
| `CREATE INDEX` per table | same indexes; partitioning by project/expert optional |
| single writer process | pooled async writers; read replicas (same SQL) |