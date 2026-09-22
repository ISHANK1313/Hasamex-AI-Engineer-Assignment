# CLAUDE.md

Expert-Call Transcript Analyzer (Hasamex AI Engineer case). Three expert-call transcripts are
analysed into guide answers, exact quotes with timestamps, themes/disagreements, and cited Q&A.

## Commands

```bash
pytest -q                                   # full suite (golden dataset, quote integrity, contracts)
pytest tests/test_analyze.py -q             # deterministic core only
pytest tests/test_llm.py -q                 # model layer, no network (uses MOCK_LLM)
uvicorn app.main:app                        # serve API + UI on http://localhost:8000
MOCK_LLM=1 uvicorn app.main:app             # offline model stand-in, no key, no network
```

Windows PowerShell: `$env:MOCK_LLM=1; uvicorn app.main:app`.

## Layout

- `app/analyze.py` - deterministic core. Parser, turn pairing, topic matching, verbatim quotes,
  themes/disagreements, lexical retrieval. **No model calls here, ever.**
- `app/llm.py` - the only place a model is called. Evidence in, prose out, citation post-check.
- `app/main.py` - routes, in-memory store, `{error:{code,message}}` envelope, upload guard.
- `static/` - single-page UI: Guide, Themes, Ask. No build step, no framework.
- `data/transcripts/`, `data/Interview_Guide.txt`, `data/golden_dataset.json`.
- `tests/` - golden dataset, quote integrity, API contracts, model layer.
- `docs/` - PRD, TRD, architecture, C4 diagrams, request flows, DB schema, phases, ADRs, evidence.

## Rules that must not be broken

1. Quotes are exact substrings of the source turn; never paraphrase inside a quote.
2. Timestamps come from the parsed file, never from a model.
3. Any model output that cites a timestamp absent from its evidence is discarded for verbatim evidence.
4. A question with no evidence answers "the transcripts do not contain evidence for that question"
   with zero citations.
5. No new dependency for something the standard library, FastAPI or an already-installed package does.

## Conventions

- Python 3.11+, standard library first. Optional model access is one `httpx.post`, no provider SDK.
- Configuration is environment variables only: `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`,
  `LLM_TIMEOUT_S`, `MOCK_LLM`. `.env` is gitignored; `.env.example` is committed.
- Frontend builds DOM nodes and sets `textContent`; transcript text is never inserted as HTML.
- Comments explain *why* (the trap that was hit), not what the line does.
- Docs describe the shipped in-memory v1 and label the SQLite/FTS5 schema as the 30+ transcript answer.
