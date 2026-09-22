# Expert-Call Transcript Analyzer

Analyses three expert-call transcripts about the European robotic surgery market: it answers the
interview guide per expert, extracts **exact quotes with the timestamp they came from**, finds the
themes and disagreements across the three calls, and lets you ask questions across all transcripts.

Built for the Hasamex AI Engineer case. The requirement that shaped every decision is
*"do not invent information"*: quotes are extracted by code as exact substrings of the transcript,
timestamps are read from the file, and an optional model is only ever allowed to write prose around
evidence the code already retrieved and verified.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn app.main:app              # then open http://localhost:8000
```

No API key is needed: the three sample transcripts load on startup and everything works in lexical
(verbatim) mode. To enable optional model-written summaries, copy `.env.example` to `.env`, add a key,
and run `uvicorn app.main:app --env-file .env`.

```bash
pytest                            # golden dataset: 18 answers, 6 themes, 4 disagreements, quote integrity
```

## How it maps to the brief

| Requirement | Where |
|---|---|
| Read/upload the 3 transcripts | bundled samples load on startup; `POST /api/transcripts/ingest` accepts an upload in the same format |
| Answer the guide per expert | `GET /api/guide-answers` - 6 questions x 3 experts, each with quotes and timestamps |
| Exact quotes | `app/analyze.py::best_quote` returns a verbatim span; tests assert every quote is a substring of its source turn |
| Source timestamp | carried from the parse (`MM:SS` from the file), shown on every quote and citation |
| Common themes and disagreements | `GET /api/themes` - a theme when 2+ experts cover a topic, a disagreement when they quantify, redirect or reject differently |
| Ask across transcripts | `POST /api/ask` - retrieval first, then verbatim evidence or model prose over that evidence |

## How accuracy is enforced

1. **Deterministic extraction first, model last.** Parsing, matching, quotes, timestamps and themes are
   plain code in `app/analyze.py`. Nothing there can hallucinate; it can only be wrong in a way a test
   catches.
2. **Quotes are exact substrings.** `tests/test_analyze.py` and `tests/test_api.py` re-read every
   displayed quote from its source segment, so a paraphrase in a quote fails the build.
3. **Citation post-check.** If a model answer cites a timestamp that was not in the evidence handed to
   it, the answer is retried once and then discarded in favour of the verbatim evidence
   (`tests/test_llm.py::test_hallucinated_citation_triggers_fallback`).
4. **No evidence means no answer.** A question the transcripts do not cover returns
   "the transcripts do not contain evidence for that question" with zero citations, instead of the
   nearest confident-sounding text.
5. **Golden dataset.** `data/golden_dataset.json` holds hand-verified expected answers, themes and
   disagreements read off the transcripts; the suite fails loudly if extraction drifts.

## Architecture

One FastAPI process serves the API and the single-page UI (no build step, no framework, no database -
the whole corpus is ~42 turns held in memory, reloaded from disk on startup).

```
static/ (index.html, app.js, style.css)
        |
app/main.py       routes, in-memory store, error envelope, upload guard
app/analyze.py    deterministic core: parser -> turn pairs -> quotes -> themes -> lexical retrieval
app/llm.py        optional OpenAI-compatible adapter (default Google Gemini free tier) + citation guard
data/transcripts  the 3 sample files, parsed on startup
data/golden_dataset.json  expected answers used by the tests
```

Transcripts are strictly paired: every interviewer turn is a paraphrase of a guide question and the
turn after it is that expert's answer, so routing a question to an expert's answer is a lookup rather
than a guess. Keyword scoring over whole transcripts was tried first and reliably picked the wrong
turn (an ROI turn as the answer about training); the pairing is what makes extraction accurate.

**Model choice.** The only thing a model is used for is phrasing: a short cross-expert summary per
guide question, and free-form answers. The default provider is Gemini's OpenAI-compatible endpoint
(free tier, cheap, fast, good at "answer only from the evidence"). Any OpenAI-compatible
`chat/completions` endpoint works by setting `LLM_BASE_URL` and `LLM_MODEL`; the call is one
`httpx.post`, so no provider SDK is needed. With no key the app degrades to verbatim excerpts, which is
the demo path.

**Scaling 3 to 30+.** Nothing depends on there being three transcripts. The same parser and citation
layer stay; retrieval swaps lexical overlap for a hybrid BM25 + vector index, theme detection swaps the
lexicon in `analyze.py` for embedding clustering, ingestion becomes parallel, and the in-memory store
becomes SQLite/FTS5 and then Postgres with pgvector. That storage design is already written down in
`docs/07-Database-Schema.md`.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness plus corpus and provider status |
| GET | `/api/transcripts` | loaded transcripts with expert, role and turn counts |
| POST | `/api/transcripts/ingest` | reload the samples, or upload one transcript (multipart `file`) |
| GET | `/api/guide-answers` | guide answers per expert with quotes and timestamps |
| GET | `/api/themes` | themes and disagreements |
| POST | `/api/ask` | `{"question": "..."}` (optional `use_llm`) -> answer plus citations |
| GET | `/api/segments/{id}` | the raw source turn behind a citation |

Errors always come back as `{"error": {"code": "...", "message": "..."}}`; a malformed upload is a 422
naming the offending line, and the loaded samples are left untouched.

## Transcript format

```
Expert 1 - Dr. Jean Martin
Role: Head of Urology
Market: France

00:18
Dr. Martin: Adoption is growing, but it is still concentrated in larger academic hospitals...
```

A timestamp line, then `Speaker: text`. Anything else before the first timestamp is header.

## Docs

Requirements, architecture, C4 diagrams, request flows, the database schema, the demo script and the
run guide are in `docs/` (start at `docs/01-PRD.md`; cheat sheet at `docs/12-Fast-Lookup.md`).
Decisions are recorded in `docs/adr/` and the pre-submission verification run in `docs/evidence/`.
