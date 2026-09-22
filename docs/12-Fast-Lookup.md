# Fast Lookup — Quick Reference Cheat Sheet

| Field | Value |
|---|---|
| **Document** | 60-second reference for me (and you) during the build and the demo |
| **Related** | [10-Reference](10-Reference.md) (full golden dataset), all other docs |

---

## 1. The 6 requirements (memo)

1. Load/read the 3 transcripts
2. Answer the interview guide **per expert**
3. Exact **quotes**
4. **Timestamp** for each answer/quote
5. **Themes** + **disagreements** across experts
6. **Ask** questions across transcripts

## 2. Project facts (always true)

- Market: European Robotic Surgery · 3 experts: FR (Dr. Jean Martin), GE (Anna Keller), UK (Dr. Emily Carter)
- 6 guide questions · 18 expected answers (6×3)
- Transcripts: 9 / 9 / 10 segments; timestamps `MM:SS` (FR 06:08, GE 06:05, UK 06:04 last answers)

## 3. Key timestamps to remember in the demo

| Topic | FR | GE | UK |
|---|---|---|---|
| Adoption | 00:18 | 00:16 | 00:14 |
| Barriers | 01:20 (capital budget) | 01:10 (cost) | 01:05 (training capacity) |
| ROI | 02:18 | 02:08 | 02:07/03:10 (balanced) |
| Training | 03:10 | 03:05 | 01:05/06:04 |
| Growth | 05:07 (15–20%) | 05:08 (high single/low double) | 04:06 (>15% in areas) |
| Timeline | 06:08 (6–12 mo) | 06:05 (9–18 mo) | 05:04 (6–9 mo, funding ready) |

## 4. Headline disagreements

- **Growth rate:** FR 15–20%/yr vs GE "not 20% across the market"
- **ROI weight:** FR/GE "economic case decides" vs UK "finance alone does not decide"
- **#1 barrier:** FR/GE budget/cost vs UK training capacity
- **Timeline:** GE 9–18 mo vs FR 6–12 / UK 6–9 mo

## 5. Design decisions (one line each)

| # | Decision |
|---|---|
| D1 | Deterministic extraction first; LLM only summarises over cited evidence |
| D2 | Quotes = exact substrings (code extracts, never paraphrased) |
| D3 | Timestamps carried as segment data from parse — never model-generated |
| D4 | SQLite + FTS5; no key → full lexical mode; LLM optional via `.env` |
| D5 | Single FastAPI process serving SPA + API (2 commands to run) |
| D6 | Golden dataset backed by pytest → "accuracy" proven mechanically |
| D7 | 3 → 30: same layers, embeddings + clustering + real DB (pgvector) |

## 6. Core commands (reference implementation)

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload      # → http://localhost:8000
pytest                             # golden-dataset tests
```

## 7. API surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/transcripts` | list loaded transcripts |
| POST | `/api/transcripts/ingest` | load samples / upload |
| GET | `/api/guide-answers` | guide answers + quotes + timestamps |
| GET | `/api/themes` | themes + disagreements |
| POST | `/api/ask` | cross-transcript Q&A (cited) |

## 8. Doc map

```
docs/
├── 01-PRD.md           product reqs (what & why)
├── 02-TRD.md           tech reqs, stack, model choice, algorithms
├── 03-Architecture.md  system design + decisions
├── 04-High-Level-Diagram.md   C4 L1-2
├── 05-Low-Level-Diagram.md    modules, classes, sequences
├── 06-Request-Flow.md  end-to-end flows per endpoint
├── 07-Database-Schema.md      SQLite DDL + FTS5 + ER
├── 07-Memory.md        state & what we don't remember
├── 08-Phases.md        build milestones
├── 09-Scratchpad.md    thinking notes (internal)
├── 10-Reference.md     golden dataset + decisions log
├── 11-Checklist.md     build/verify/demo/submit checklist
├── 12-Fast-Lookup.md   ← you are here
└── docs-extra/
    ├── 13-Demo-Script.md      video script
    ├── 14-Submission-Plan.md  manual vs automated steps
    └── 15-Run-Guide.md        local run instructions
```