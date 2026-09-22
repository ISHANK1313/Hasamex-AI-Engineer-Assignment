# Phases — Build Plan & Milestones

| Field | Value |
|---|---|
| **Document** | Phases / execution plan |
| **Version** | v0.1 |
| **Status** | Build complete (phases 1-6). Phase 7 (video, push, submit) is manual. |
| **Related docs** | [01-PRD](01-PRD.md), [02-TRD](02-TRD.md), [11-Checklist](11-Checklist.md) |

> **Delivery note (2026-09-22):** phases 1-6 were built and verified against the same scope with a
> flatter, smaller implementation than the module tree sketched below: `app/analyze.py` (parser,
> turn pairing, matcher, quotes, themes, retrieval), `app/llm.py` (optional model layer) and
> `app/main.py` (routes, in-memory store), plus `static/` for the UI. No SQLite and no per-layer
> packages, because the corpus is three transcripts held in memory
> ([adr/0001](adr/0001-in-memory-store.md)). The phase list is kept as the plan of record; the
> verification run is in [evidence/verification.md](evidence/verification.md).

---

## Phase 0 — Confirm (with user, 1 question round)
- **Stack decision:** Python/FastAPI (recommended, fastest demo) vs Java Spring Boot.
- **LLM provider:** OpenAI-compatible vs local-only mode (no-key default).
- **Deliverable:** this doc set finalised; stack note recorded in 02-TRD §2.

## Phase 1 — Scaffold & data layer
- [ ] `requirements.txt`, `pyproject`, `app/` package skeleton, `.env.example`, `.gitignore`
- [ ] `models/` (Segment, Transcript, DTOs) · `storage/db.py` schema v1 (07-Database-Schema DDL)
- [ ] `ingest/parser.py` + header/line parsers; parse the 3 sample transcripts
- [ ] Tests: `test_parser.py` (9 segments each, header parse)
- **Exit:** samples ingest; segments + FTS5 built; 3 tests green.

## Phase 2 — Guide answers + quotes (core value)
- [ ] `guide_service` QuestionMatcher (lexicon per Q1–Q6) + QuoteExtractor (exact substring)
- [ ] `/api/guide-answers` endpoint; golden dataset (10-Reference §4) regression tests
- [ ] `not_covered` handling
- **Exit:** all 18 answers (6×3) with verbatim quotes + timestamps, tests green.

## Phase 3 — Themes & disagreements
- [ ] `theme_service` topic buckets + stance/polarity detection
- [ ] `/api/themes`; golden theme/disagreement tests (10-Reference §5)
- **Exit:** expected themes + disagreements appear with per-expert quotes.

## Phase 4 — Q&A (cross-transcript)
- [ ] FTS5 retrieval (`search.py`) + evidence pack builder
- [ ] `/api/ask` lexical mode (no key)
- [ ] LLM gateway + prompts + citation post-check (optional key)
- [ ] `qa_log`; no-key integration tests
- **Exit:** `/ask` returns cited answers in both modes.

## Phase 5 — UI & polish
- [ ] `static/` SPA: Guide tab, Themes tab, Ask tab, Upload; timestamps + copy-quote
- [ ] Error banners (parse errors, no evidence, LLM down)
- **Exit:** full user flow clickable end-to-end.

## Phase 6 — Hardening & docs
- [ ] README (run instructions) + demo script (`docs-extra/demo-script.md`)
- [ ] Edge tests (malformed files, empty corpus, special-char questions)
- [ ] Final accuracy pass vs golden dataset; `.env` optional LLM verify
- **Exit:** repo ready for submission.

## Phase 7 — Submission
- [ ] Push repo (GitHub public)
- [ ] README + docs link; record demo video (see 11-Checklist §Demo)
- [ ] Submit form: repo URL, run instructions, video, README
- **Exit:** submission complete.

## Milestone mapping to demo requirements

| Demo requirement (README_CASE) | Phase |
|---|---|
| Upload/read 3 transcripts | 1 |
| Answer interview guide per expert | 2 |
| Extract exact quotes | 2 |
| Show source timestamp | 2 (rendered in 5) |
| Common themes + disagreements | 3 |
| Ask questions across transcripts | 4 |
| Architecture / model choice / citations / hallucination control / scaling explanation | 6 + video |