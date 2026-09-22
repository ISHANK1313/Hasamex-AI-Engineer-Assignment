# Checklist — Build, Verify, Demo, Submit

| Field | Value |
|---|---|
| **Document** | Master checklist (work in progress; check off as you go) |
| **Related** | [08-Phases](08-Phases.md), [01-PRD](01-PRD.md) |

---

## A. Core requirements (from assignment brief)

- [x] App reads/uploads the 3 sample transcripts
- [x] Answers the interview guide for **each expert** (6 questions × 3 experts)
- [x] Extracts **exact quotes** (verbatim substrings)
- [x] Shows **source timestamp** for every answer/quote
- [x] Identifies **common themes** across all 3 experts
- [x] Identifies **disagreements** across experts
- [x] User can **ask questions** across all transcripts
- [x] No invented information; every important answer traceable

Verified 2026-09-22 - see [evidence/verification.md](evidence/verification.md).

## B. Demo explanation bullets (README_CASE "Important")

- [x] Architecture explained (root `README.md`, [03-Architecture](03-Architecture.md), [05-Low-Level-Diagram](05-Low-Level-Diagram.md))
- [x] Model choice explained (README "Model choice", [02-TRD](02-TRD.md) §3, [adr/0002](adr/0002-deterministic-extraction-first.md))
- [x] How citations/timestamps are handled (README "How accuracy is enforced", [adr/0002](adr/0002-deterministic-extraction-first.md))
- [x] How hallucinations are reduced (same, plus the citation-guard tests in `tests/test_llm.py`)
- [x] How to scale from 3 → 30+ transcripts (README "Scaling 3 to 30+", [07-Database-Schema](07-Database-Schema.md), [adr/0001](adr/0001-in-memory-store.md))
- [ ] Speaking these answers on camera is the manual recording step

## C. Engineering quality

- [x] Golden dataset tests green (18 answers + themes + disagreements) - 66 passed
- [x] Quote integrity test: every quote `source.contains(quote)`
- [x] No-key mode verified (no `.env` needed)
- [x] Parse error handling (malformed upload → clear 422 with file and line)
- [x] `requirements.txt` + `.env.example` + `.gitignore` (key not committed)
- [~] SQLite schema migration v1 idempotent - **N/A in v1**: the shipped app is in-memory, so there is
      no migration to run. The schema is the documented 3 → 30 path ([adr/0001](adr/0001-in-memory-store.md)).

## D. Submission pack

- [x] Working app or local run instructions (README)
- [~] Source code repository - local repo initialised and committed; the GitHub push is manual
- [x] Short README
- [ ] Demo video recorded (see demo script: [13-Demo-Script](docs-extra/13-Demo-Script.md))
- [ ] Submit form completed (repo URL, run instructions, video link)

## E. Demo video (5–10 min suggested)

- [ ] 0:00–0:30 What I built + how it maps to the 6 requirements
- [ ] 0:30–1:30 Load transcripts → parsed segments with timestamps
- [ ] 1:30–3:00 Guide answers: summary + exact quotes + timestamps
- [ ] 3:00–4:00 Themes & disagreements
- [ ] 4:00–5:00 Ask a question → cited answer → backlink to segment
- [ ] 5:00–6:30 Hallucination controls (verbatim quotes, citation check, no-key mode)
- [ ] 6:30–8:00 Scaling 3 → 30+: index, clustering, real DB
- [ ] 8:00–9:00 `pytest` run — accuracy is mechanically proven
- [ ] 9:00–10:00 Wrap-up: stack, decisions, what I'd do next

## F. Pre-submission smoke test (1 run through)

- [x] `pip install -r requirements.txt`
- [x] `uvicorn app.main:app` → http://localhost:8000 loads
- [x] Guide tab: 6 questions × 3 experts all render with quotes + timestamps
- [x] Themes tab: themes + disagreements present
- [x] Ask tab: type "How long does purchasing a robot take?" → 3 cited answers (FR/GE/UK)
- [x] Upload a broken file → friendly error naming the file and line
- [x] Unset API key → app still fully works

---

*Checklist maintained alongside 08-Phases.md; mark items only when actually done.*