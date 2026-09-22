# Run Guide — Local Setup (short version for submission)

| Field | Value |
|---|---|
| **Document** | Local run instructions (mirrors the README) |
| **Stack** | Python 3.11+, FastAPI, SQLite (reference implementation) |

---

## 1. Prerequisites

- Python 3.11 or newer
- Git (for the repo)
- *(Optional)* an OpenAI-compatible API key if you want generative summaries (not required)

## 2. Run it

```bash
# 1) clone (or open the project folder)
git clone <your-repo-url>
cd <project-folder>

# 2) install
python -m venv .venv
source .venv/bin/activate          # Windows (Git Bash): source .venv/Scripts/activate
pip install -r requirements.txt

# 3) run
uvicorn app.main:app --reload

# 4) open
# http://localhost:8000
```

> The three sample transcripts load automatically on startup. **No API key needed** — the app runs in
> lexical mode; to enable the optional LLM summaries, copy `.env.example` to `.env` and add your key.

## 3. Run the tests (accuracy proof)

```bash
pytest            # golden dataset: 18 guide answers, themes, disagreements, quote integrity
```

## 4. API cheatsheet

| Endpoint | Use |
|---|---|
| `GET /api/health` | liveness |
| `GET /api/transcripts` | list loaded transcripts |
| `POST /api/transcripts/ingest` | load samples / upload a transcript file |
| `GET /api/guide-answers` | guide answers + quotes + timestamps |
| `GET /api/themes` | common themes + disagreements |
| `POST /api/ask` | `{"question": "How long does purchasing take?"}` → cited answer |

## 5. Troubleshooting

| Symptom | Fix |
|---|---|
| `uvicorn: command not found` | activate venv; or `python -m uvicorn app.main:app` |
| Port 8000 busy | `uvicorn app.main:app --port 8001` |
| Upload fails on a custom file | keep the `MM:SS Speaker: text` line format |
| Want LLM mode | create `.env` with `OPENAI_API_KEY=...` then restart |