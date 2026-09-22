# 🛠️ How to Run This Project Locally

Everything you need to get the app running on your machine in about two minutes. The app works with **no API key**; AI-written summaries are optional.

---

## 1. Prerequisites

| Need | Why | Check |
|------|-----|-------|
| **Python 3.11 or newer** | App targets 3.11+ syntax | `python --version` |
| A terminal | PowerShell, Command Prompt, bash, or zsh all work | — |
| Internet | Only for `pip install` and (if you add a key) model calls. Demo runs fully offline. | — |

Optional: OpenAI-compatible API key (Google Gemini free tier is default) for AI-written summaries instead of verbatim quotes.

---

## 2. Get the Project

```bash
git clone <your-repo-url>
cd <project-folder>
```

Or open the folder if you already have it.

---

## 3. Create Virtual Environment & Install

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Five dependencies: FastAPI, Uvicorn, httpx, python-multipart, pytest. No Node, no Docker, no database.

---

## 4. Run the App

```bash
uvicorn app.main:app
```

Then open **http://localhost:8000**.

Run from the project root (folder containing `app/` and `static/`).

---

## 5. What You Should See

On startup, server log prints:

```
INFO app: loaded 3 transcripts, 6 guide questions
INFO app: answer mode: verbatim evidence only (no LLM_API_KEY in .env)
```

In the browser:
- Status line → **"ready: 6 guide questions across 3 experts."**
- Chips listing three transcripts (42 turns total) and active answer mode
- Three tabs: **Guide answers**, **Themes and disagreements**, **Ask across transcripts**

If status stays on "loading" or error banner appears → [Troubleshooting](#9-troubleshooting).

---

## 6. Optional: Enable AI-Written Summaries

The app reads `.env` in project root automatically. Create one (or copy `.env.example`):

```ini
LLM_API_KEY=your-key-here
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_MODEL=gemini-2.0-flash
```

Restart server. Startup line reads `answer mode: gemini-2.0-flash`; UI chip switches from "no key: verbatim mode" to model name.

- `.env` is gitignored; your key never committed.
- Real env var always wins over `.env`: `LLM_MODEL=something-else uvicorn app.main:app` overrides for one run.
- Any OpenAI-compatible endpoint works — change `LLM_BASE_URL` and `LLM_MODEL` (OpenAI, OpenRouter, local server, etc.).
- Wrong/expired key? Nothing breaks: app logs warning, answers from verbatim evidence with note explaining why.

---

## 7. Run Tests (Accuracy Proof)

```bash
pytest -q
```

Expect **66 passed**. Suite is fully offline: forces "no key" for every test, never calls model even if `.env` has real key.

Useful slices:

```bash
pytest tests/test_analyze.py -q     # golden dataset: 18 answers, themes, disagreements, quote integrity
pytest tests/test_api.py -q         # route and response contracts, upload handling
pytest tests/test_llm.py -q         # citation guard: fabricated timestamps rejected, fallbacks
```

---

## 8. Things to Try

| Ask This | Expected Result |
|----------|-----------------|
| "How long does purchasing a robotic system take?" | 3 citations: FR 06:08, GE 06:05, UK 05:04 |
| "What are the main barriers to adoption?" | 3 citations: FR 01:20, GE 01:10, UK 01:05 |
| "Is growth going to be fast?" | 3 citations: FR 05:07, GE 05:08, UK 04:06 |
| "What is the capital of Peru?" | 0 citations, explicit "the transcripts do not contain evidence for that question" |

Click any timestamp chip's **Source turn** button to see full transcript turn a quote came from — traceability made clickable.

### Upload Your Own Transcript

Expected format:

```
Expert 4 - Dr. Test
Role: Surgeon
Market: Spain

00:00
Interviewer: How would you describe adoption?

00:10
Dr. Test: Adoption is growing steadily here.
```

Rules: timestamp line (`MM:SS`) followed by `Speaker: text`; anything before first timestamp = header; UTF-8 text (BOM tolerated); up to 2 MB. Malformed file rejected with message naming file and offending line; loaded samples stay untouched.

---

## 9. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `uvicorn: command not found` | Virtual env not active, or use `python -m uvicorn app.main:app` |
| `ModuleNotFoundError: app` | Run command from project root (folder with `app/` in it) |
| Port 8000 already in use | `uvicorn app.main:app --port 8001`, open http://localhost:8001 |
| UI chip says "no key: verbatim mode" but you expected summaries | `.env` missing, empty, or wrong key name. Must be `LLM_API_KEY=...` in project root, then restart |
| Answer has note like `model unavailable: provider returned 400` | Key rejected. Verbatim answer shown is still correct and cited; fix key for prose |
| `pip install` slow | Normal on cold cache. Nothing else needed after. |
| Upload rejected | Keep `MM:SS` + `Speaker: text` format; error message tells exact line |
| Want to stop server | `Ctrl+C` in terminal running Uvicorn |

---

## 10. API Cheatsheet

```bash
# liveness, corpus size, active answer mode
curl http://localhost:8000/api/health

# all guide answers with quotes and timestamps
curl http://localhost:8000/api/guide-answers

# themes and disagreements
curl http://localhost:8000/api/themes

# ask a question across every transcript
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"How long does purchasing a robotic system take?\"}"

# raw transcript turn behind any citation
curl http://localhost:8000/api/segments/France:06:08:Dr.%20Martin

# reload bundled samples
curl -X POST http://localhost:8000/api/transcripts/ingest

# upload a transcript
curl -X POST http://localhost:8000/api/transcripts/ingest -F "file=@my_transcript.txt"
```

Interactive API docs while server runs: **http://localhost:8000/docs**

---

## 11. Where Everything Lives

| Path | What |
|------|------|
| `app/main.py` | Routes, in-memory store, error envelope, upload guards, static mount |
| `app/analyze.py` | Parser, turn pairing, topic matching, verbatim quotes, themes, retrieval (no model calls) |
| `app/llm.py` | Optional model layer: prompt, call, citation post-check, `.env` reader |
| `static/` | Single-page UI (Guide, Themes, Ask) |
| `data/transcripts/` | Three sample transcripts, parsed on startup |
| `data/golden_dataset.json` | Hand-verified expectations tests assert against |
| `tests/` | Golden dataset, API contracts, model-layer guard |
| `docs/adr/`, `docs/evidence/` | Architecture decisions, verification report |
| `.env` | Your optional key (gitignored). Template in `.env.example` |

---

## 12. Verify Everything Works

Run these three checks in order:

1. **Tests pass:** `pytest -q` → `66 passed`
2. **Server starts:** `uvicorn app.main:app` → log shows "loaded 3 transcripts, 6 guide questions"
3. **UI loads:** Open http://localhost:8000 → status shows "ready: 6 guide questions across 3 experts"

If all three ✅, you're ready to demo.

---

Back to overview: **[README.md](README.md)**