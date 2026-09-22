# PRD — Expert-Call Transcript Analyzer (Hasamex AI Engineer Case)

| Field | Value |
|---|---|
| **Document** | Product Requirements Document |
| **Version** | v0.1 (Draft) |
| **Status** | Planning — approved to build after Phase 0 confirmations |
| **Author** | AI Engineering Agent (ZCode) |
| **Related docs** | [02-TRD](02-TRD.md), [03-Architecture](03-Architecture.md), [10-Reference](10-Reference.md) |

---

## 1. Problem Statement

A research team conducts expert interview calls (3 or more) about the same market/project topic.
Today, an analyst must read every transcript manually, map answers to an interview guide, hunt for
exact quotes, find timestamps, and spot themes/disagreements across calls. This is slow, error-prone,
and hard to defend because claims lose their traceability back to the source recording.

The case asks us to build a **simple application** that automates this with AI while keeping every
claim traceable to the exact transcript segment and timestamp.

## 2. Goal

> "Build a simple app that analyses 3 expert-call transcripts from the same project."

The app must:
1. Read/upload the 3 sample transcripts.
2. Answer the interview-guide questions **for each expert**.
3. Extract **useful exact quotes**.
4. Show the **source timestamp** for each answer/quote.
5. Identify **common themes and disagreements** across all 3 experts.
6. Let the user **ask questions across all transcripts**.

## 3. Project Context (grounded in case pack)

- **Market studied:** European Robotic Surgery Market.
- **Experts:**
  - Dr. Jean Martin — Head of Urology — France (`Transcript_1_France.txt`)
  - Anna Keller — Former Hospital Procurement Director — Germany (`Transcript_2_Germany.txt`)
  - Dr. Emily Carter — Consultant Urologist — United Kingdom (`Transcript_3_UK.txt`)
- **Interview guide:** 6 questions (see [10-Reference](10-Reference.md) §3).
- Each transcript is short (~9 dialogue turns, timestamps in `MM:SS` format).

## 4. Users & Personas

| Persona | Who | What they need |
|---|---|---|
| **Research Analyst (end user)** | Person who reads expert calls | Fast, trustworthy, cited answers; themes across calls |
| **Interview Panel (evaluator)** | Hasamex AI Engineering hiring team | Working app, clear architecture, accuracy, explainability |
| **Candidate (you)** | The one submitting the case | A demo-able app + clear story (architecture, model choice, citations, hallucination control, scaling) |

## 5. Scope

### 5.1 In scope (v1)
- Ingest the 3 bundled transcripts (file upload **and** built-in sample loading — no network needed).
- Deterministic parse of transcripts into `speaker` + `timestamp` + `text` segments.
- Per-expert answers to the 6 guide questions, each with verbatim quotes + timestamps.
- Cross-expert theme and disagreement summary.
- Free-form Q&A across all transcripts with citations (hybrid: lexical + optional LLM).
- Simple single-page UI: list view (per expert) + themes view + ask view.
- Local run instructions, README, tests, demo script.

### 5.2 Out of scope (v1)
- Authentication, multi-user, cloud deployment.
- Audio/video transcription (transcripts are given as text).
- Support for arbitrary transcript formats beyond the given one (parser is format-aware but generic enough).
- Advanced analytics (sentiment, entity networks) — nice-to-have backlog.

## 6. User Stories & Acceptance Criteria

### US-1 — Load transcripts
**As an analyst, I can load the 3 transcripts so I can analyse them.**

- AC1.1: App starts with the 3 sample transcripts pre-loaded (zero setup).
- AC1.2: User can also upload a transcript file matching the format; it appears in the app.
- AC1.3: Each transcript is parsed into segments with speaker, timestamp, and text.
- AC1.4: Parse errors are shown clearly (e.g., "line 12 has no timestamp").

### US-2 — Guide answers per expert
**As an analyst, I can see the interview-guide answered for each expert, with quotes and timestamps.**

- AC2.1: For each of the 6 guide questions, each expert has an answer.
- AC2.2: Under each answer the app shows **verbatim supporting quotes** (exact substring of the transcript).
- AC2.3: Every quote displays its **source timestamp** (e.g., `01:20`) and expert.
- AC2.4: Where an expert did not address the question, the app says "Not covered" — it never invents an answer.
- AC2.5: **Accuracy check:** all 18 possible answers (6 × 3 experts) match the golden dataset in [10-Reference](10-Reference.md) §4.

### US-3 — Themes & disagreements
**As an analyst, I can see what all experts agree on and where they disagree.**

- AC3.1: A "Common themes" section lists recurring topics across ≥2 experts with supporting quotes.
- AC3.2: A "Disagreements" section surfaces contrasting views, showing each side's quotes.
- AC3.3: Golden dataset items (e.g., growth-rate disagreement, ROI importance) all appear (see Reference §5).
- AC3.4: Every theme/disagreement line is clickable through to source quotes.

### US-4 — Ask questions across transcripts
**As an analyst, I can ask any question and get an answer grounded in the transcripts.**

- AC4.1: User types a question; app returns an answer + the supporting segments/quotes it used.
- AC4.2: Every claim in the answer maps to ≥1 segment with timestamp.
- AC4.3: If evidence is insufficient, the app answers with the closest snippets and says so — it never fabricates.
- AC4.4: Works with **zero API key** (lexical retrieval + verbatim snippets direct from source).

### US-5 — Demo & explanation (evaluator-facing)
**As an evaluator, I can see the key requirements demonstrated in a short video.**

- AC5.1: Demo covers: architecture, model choice, citation/timestamp handling, hallucination reduction, 3 → 30+ scaling.
- AC5.2: Repo contains source, run instructions, README.

## 7. Functional Requirements (prioritised)

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Ingest bundled transcripts automatically | Must |
| FR-2 | Parse `MM:SS` + speaker + text segments | Must |
| FR-3 | Map each guide question to relevant segments per expert | Must |
| FR-4 | Extract verbatim quotes with char-range integrity check | Must |
| FR-5 | Render timestamps next to every quote/answer | Must |
| FR-6 | Compute common themes across experts | Must |
| FR-7 | Compute disagreements across experts | Must |
| FR-8 | Free-form Q&A with citation (lexical baseline) | Must |
| FR-9 | Optional LLM synthesis for Q&A & answer phrasing (API key) | Should |
| FR-10 | Upload custom transcript files | Should |
| FR-11 | Golden-dataset regression tests (18 answers, themes) | Must |
| FR-12 | Export summary (markdown/PDF) | Could |

## 8. Non-Functional Requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-1 | **Traceability** | 100% of displayed answers/quotes have source segment + timestamp |
| NFR-2 | **No fabrication** | 0 invented quotes; "not covered" shown when no evidence |
| NFR-3 | **Simplicity** | UI usable by a non-technical analyst in < 2 min |
| NFR-4 | **Runs locally** | Two commands max (install + run), no paid services required |
| NFR-5 | **Speed** | Guide answers + themes render < 2s; Q&A < 5s (with LLM, cached) |
| NFR-6 | **Extensible** | Adding transcript #4..#30 doesn't change the architecture |
| NFR-7 | **Demo-able** | Works offline; LLM optional via `.env` |

## 9. Success Metrics / Demo Pass Checklist

- [ ] App loads with 3 transcripts pre-ingested.
- [ ] All 6 guide questions answered per expert; each has ≥1 verbatim quote + timestamp.
- [ ] Themes list shows ≥ (see Reference §5) expected themes.
- [ ] Disagreements list shows the expected disagreements (ROI, growth rate, timeline, training-as-barrier).
- [ ] Q&A answers a question with correct cited segments (e.g., "How long does a purchase take?" uses the 3 timeline quotes).
- [ ] No fabricated data anywhere (spot-check every quote against source).
- [ ] Works without API key.

## 10. Constraints & Guardrails

- **Do not invent information.** All content must be traceable to transcript text.
- **Every important answer traceable** to transcript (segment + timestamp).
- **Keep the UI simple and usable** (explicitly requested by the case).
- Must be explainable in a short demo video (architecture, model choice, citations, hallucination control, scaling).