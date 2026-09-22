# 🎙️ Expert-Call Transcript Analyzer

**Feed it three expert-call transcripts. Get guide answers per expert, exact quotes with timestamps, themes and disagreements across calls, and cited answers to any question you ask.**

Built for the Hasamex AI Engineer case (European Robotic Surgery market). Core principle: **never invent information**. Quotes are exact substrings extracted by code, timestamps come from the file, and an optional AI model only writes prose around evidence already retrieved and verified.

`Python 3.11` · `FastAPI` · `Vanilla JS SPA` · `In-memory` · `Optional OpenAI-compatible model` · **Zero API key required** · `66 tests`

---

## ✨ What It Does

| Requirement | Implementation |
|-------------|----------------|
| 📂 Load 3 transcripts | Bundled samples load on startup; upload adds a 4th in same format |
| ❓ Answer interview guide **per expert** | `GET /api/guide-answers` — 6 questions × 3 experts, each with quotes + timestamps |
| 💬 Extract **exact quotes** | Verbatim spans of source turns; every quote asserted as substring of source |
| ⏱️ Show **source timestamps** | `MM:SS` from parse on every quote, citation, and source view |
| 🔗 Find **common themes** | 2+ experts on a topic = theme, showing each expert's own words |
| ⚖️ Find **disagreements** | Detected from differing numbers, explicit rejection, or different primary driver |
| 🧠 **Ask questions** across calls | `POST /api/ask` — retrieval first, then verbatim evidence or model prose over evidence |

---

## 🧱 Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Language | Python 3.11 | Fastest path to demoable, testable pipeline |
| Web Framework | FastAPI + Uvicorn | Async, self-documenting `/docs`, minimal |
| Frontend | 3 static files (HTML + vanilla JS + CSS) | No build step, no framework, served by same process |
| Storage | In-memory (42 turns) | Database for 5 KB text = scaffolding; SQLite/FTS5 design in docs for 3→30 |
| AI (Optional) | Any OpenAI-compatible `chat/completions` endpoint | One `httpx.post`, no provider SDK, swappable by env var |
| Tests | pytest | Golden dataset: 18 answers, 6 themes, 4 disagreements, quote integrity |

**5 dependencies, no build step, no database, no Docker.**

---

## 🏗️ Architecture

```
Browser (static/index.html + app.js + style.css)
    |  fetch /api/*
    v
app/main.py ------ 6 routes . in-memory store . {error:{code,message}} envelope . upload guards
    |
    +-- app/analyze.py   DETERMINISTIC CORE (no model, ever)
    |     parse "MM:SS + Speaker: text"  -> segments (timestamps from file)
    |     pair turns: interviewer question -> expert answer
    |     topic match: guide question -> evidence turns -> verbatim quote spans
    |     themes (2+ experts) and disagreements (quantify / redirect / reject)
    |     lexical retrieval for free-form questions
    |
    +-- app/llm.py       OPTIONAL MODEL LAYER
          evidence in -> prose out -> citation post-check -> else verbatim fallback
```

**Accurate by construction:** extraction, matching, quoting, and theme detection are plain code. The model only phrases sentences—it never produces quotes or timestamps.

---

## 🚀 Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn app.main:app              # open http://localhost:8000
```

That's it. Three sample transcripts load automatically. **Works with NO API key.**

Want AI-written summaries? Add your key to `.env` and restart:

```ini
LLM_API_KEY=your-key
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_MODEL=gemini-2.0-flash
```

> Detailed setup, troubleshooting, and API cheatsheet: **[INSTRUCTIONS.md](INSTRUCTIONS.md)**

---

## 🖥️ The App in Three Tabs

| Tab | What You Get |
|-----|--------------|
| **Guide Answers** | One card per question, one row per expert: short summary, exact quote(s), timestamp + speaker chip, **Source turn** button revealing raw transcript turn, copy-quote. Filter box to find questions. |
| **Themes & Disagreements** | Theme cards (2+ experts, each with their quote) and disagreement cards showing *why* (differing numbers / explicit rejection / different primary driver). |
| **Ask Across Transcripts** | Type anything; get answer, provider badge, cited sources with timestamps and source-turn reveal. Nothing fabricated: off-topic = "no evidence" with zero citations. |

Plus upload of a transcript in same format (friendly error naming file and line if malformed) and "reload samples" button.

---

## 🛡️ How Hallucination Is Prevented (The Interesting Part)

1. **Deterministic first, model last.** Parsing, matching, quote extraction, timestamps, themes = code. Nothing for model to get wrong.
2. **Quotes are exact substrings.** Every displayed quote asserted as substring of its source turn—in tests and through API.
3. **Timestamps come from the file.** Never generated, always carried from parse.
4. **Citation post-check.** If model cites timestamp not in evidence, retried once then discarded for verbatim evidence.
5. **No evidence, no answer.** Off-topic question returns "transcripts do not contain evidence" with zero citations.
6. **Golden dataset.** `data/golden_dataset.json` holds hand-verified expectations—regression fails build, not demo.

---

## ✅ Verification

```bash
python -m pytest -q     # 66 passed
```

Covered: all 18 guide answers against golden timestamps/wording, quote integrity, 6 themes + 4 disagreements, retrieval per expert, citation guard (fabricated timestamp rejected), no-key mode (zero network calls), every API contract field, upload handling (valid, UTF-8 BOM, malformed, non-UTF-8, oversized).

Verified in real browser: every tab, filter, source-turn reveal, ask flow, no-evidence state, valid/broken uploads, layout at 375/768/1440 px, dark mode, zero console errors. Full report: **[docs/evidence/verification.md](docs/evidence/verification.md)**

---

## 📡 API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Liveness + corpus size + active answer mode |
| GET | `/api/transcripts` | Loaded transcripts (expert, role, turns, duration) |
| POST | `/api/transcripts/ingest` | Reload samples or upload one transcript (`file` multipart) |
| GET | `/api/guide-answers` | Guide answers with quotes + timestamps (`?use_llm=false` for verbatim) |
| GET | `/api/themes` | Themes and disagreements |
| POST | `/api/ask` | `{"question": "..."}` → `{answer, provider, citations[]}` |
| GET | `/api/segments/{id}` | Raw source turn behind a citation |

Errors: `{"error": {"code": "...", "message": "..."}}`

---

## 📁 Project Structure

```
app/
  main.py        6 routes, in-memory store, error envelope, upload guards, static mount
  analyze.py     parser, turn pairing, topic matching, verbatim quotes, themes, retrieval
  llm.py         optional model layer, prompts, citation post-check, .env reader
static/          index.html + app.js + style.css  (Guide | Themes | Ask + upload)
tests/           test_analyze.py (golden dataset) . test_api.py (contracts) . test_llm.py (guard)
data/
  transcripts/   3 sample transcripts (parsed on startup)
  golden_dataset.json   hand-verified expectations used by tests
docs/
  adr/           three decisions: in-memory store, deterministic-first, no-key default
  evidence/      verification report for this submission
INSTRUCTIONS.md  setup, troubleshooting, cheatsheet
```

---

## 📈 Scaling 3 → 30+ Transcripts

Nothing in architecture depends on three transcripts.

- **Keep:** parser, turn-pairing/citation layer, API, UI
- **Swap:** lexical retrieval → hybrid BM25 + vector index; theme lexicon → embedding clustering; sequential ingest → worker pool
- **Storage:** in-memory → SQLite + FTS5 → Postgres with pgvector behind same call sites

---

## ⚠️ Honest Limitations

- Theme/disagreement detection uses lexicon tuned to this 6-question guide. Different guide = update topic terms (documented in ADRs).
- Retrieval is lexical, not semantic: sparse two-word question whose only topical word is one of them returns "no evidence" rather than a stretch. Deliberate trade for never answering from weak match.
- Uploads live in memory for demo, lost on restart; no user accounts; audio transcription out of scope (transcripts given as text).