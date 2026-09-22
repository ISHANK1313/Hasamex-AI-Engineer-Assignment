# Verification Report - pre-submission run

| Field | Value |
|---|---|
| Date | 2026-09-22 |
| Environment | Windows, Python 3.11.9, `.venv`, no `LLM_API_KEY` set (no-key mode) |
| Result | **PASS** - all checks below ran against the real app, not mocks |

## 1. Automated tests

```
python -m pytest -q   ->  66 passed, 1 warning
```

The warning is a Starlette deprecation notice from `TestClient` (`anyio.abc.BlockingPortal`), not from
this code. Coverage of the checks that matter:

| What | Test |
|---|---|
| All 18 guide answers match the golden timestamps and wording | `tests/test_analyze.py::test_answers_match_golden_timestamp_and_wording` |
| Every displayed quote is an exact substring of its source turn | `test_every_quote_is_verbatim_and_carries_a_timestamp` |
| 6 themes and 4 disagreements match the golden topics and sides | `test_themes_cover_every_expected_topic`, `test_disagreements_match_golden_topics`, `test_golden_disagreement_sides_quote_the_right_experts` |
| A question is not answered with another question's turn | `test_a_question_answer_is_not_labelled_with_another_topic` |
| Retrieval finds the right evidence for every expert | `test_retrieval_finds_the_evidence_for_every_expert` |
| Fabricated citation is rejected and falls back | `tests/test_llm.py::test_hallucinated_citation_triggers_fallback` |
| No key means no network call at all | `test_answer_never_calls_the_model_when_no_key_and_no_mock` |
| Route and response contracts (field-by-field) | `tests/test_api.py` |
| Upload: valid, BOM-prefixed, malformed (422 + line number), non-UTF-8, oversized | `tests/test_api.py` |

## 2. Live API (uvicorn on :8000, no key)

| Check | Result |
|---|---|
| `GET /api/health` | `{"status":"ok","transcripts":3,"segments":42,"llm":"lexical","llm_available":false}` |
| `GET /api/guide-answers` | 6 questions x 3 experts; timestamps match `data/golden_dataset.json` exactly (Q1 00:18/00:16/00:14 ... Q6 06:08/06:05/05:04) |
| `GET /api/themes` | 6 themes, 4 disagreements (`growth`, `cost_roi`, `barriers`, `timeline`) |
| `POST /api/ask` "How long does purchasing a robotic system take?" | `provider=lexical`, `topic=timeline`, 3 citations (05:04, 06:05, 06:08), answer is verbatim transcript text |
| `POST /api/ask` "What is the capital of Peru?" | 0 citations, answer "The transcripts do not contain evidence for that question." |
| `GET /api/segments/France:00:18:Dr. Martin` | 200 with the full source turn |
| `POST /api/transcripts/ingest` (no file) | reloads the three samples |

## 3. Browser pass (agent-browser, Chrome, against `http://localhost:8000`)

| Check | Result |
|---|---|
| Page loads, corpus chips show 3 transcripts / 42 turns / no-key mode | PASS |
| Guide tab: 6 questions, 3 expert cards each, quote + timestamp + speaker chips | PASS |
| Filter box narrows the question list | PASS |
| "Source turn" reveals the raw transcript turn and toggles to "Hide source" | PASS |
| Themes tab: 6 theme cards and 4 disagreement cards with quotes and reasons | PASS |
| Ask tab: question -> answer, provider chip, cited sources with the expected timestamps | PASS |
| No-evidence question renders "0 cited sources" and the explicit no-evidence line | PASS |
| Upload a valid transcript -> "Added Dr. Test (2 turns)." and the corpus grows to 4 | PASS |
| Upload a broken transcript -> error banner names the file and line, corpus stays at 3 | PASS |
| Server killed mid-session -> banner shows "Failed to fetch"; no stale answer is shown | PASS |
| No horizontal overflow at 375 / 768 / 1440 px (`scrollWidth <= innerWidth` on every tab) | PASS |
| Dark mode (`prefers-color-scheme: dark`) and the tab keyboard/aria states | PASS |
| Console errors / page errors | none |

Screenshots from this run are in `docs/evidence/` (gitignored).

## 4. Defects found during this pass and fixed

| # | Symptom | Root cause | Fix |
|---|---|---|---|
| 1 | "What is the capital of Peru?" returned 4 cited confident answers | `lexical_search` treated one shared word as evidence ("capital" matched "capital budgets" in half the corpus), so the no-evidence path was unreachable | require two matching content terms (or the one the question has) - `app/analyze.py` |
| 2 | Q1 "Current adoption" showed the barriers turn as an adoption quote | the second-pair gate accepted any question mentioning the topic, and the barriers question is literally "What is holding adoption back?" | extra pairs must be exclusively about the topic; kept pairs re-sorted chronologically - `app/analyze.py`, pinned by a new test |
| 3 | A transcript saved with a UTF-8 BOM (Notepad/PowerShell default) failed as a malformed header | the BOM stayed glued to the first header line | strip a leading BOM in `parse_transcript`, pinned by a new test |
| 4 | 39 px horizontal overflow at 375 px width | `min-width: 100%` on the filter input inside a flex row | narrow-width rules: wrap rows, `flex: 1 1 100%`, `min-width: 0` - `static/style.css` |

## 5. Not verified here (honest scope)

1. **The successful live model call.** No valid `LLM_API_KEY` was available (`.env` was empty and no
   key was set in the environment), so the branch where the provider returns prose with citations was
   not exercised. Everything else on that path was verified with a placeholder key - see section 6.
2. **"Reload samples" button click.** The endpoint it calls is covered by
   `test_ingest_reloads_bundled_samples` and was verified live; the 5-line UI handler was not clicked in
   this pass.
3. **Recording the demo video and pushing the repo** are manual steps (the demo script lives in
   `docs/docs-extra/`, a local working note not shipped in this repo).

## 6. Model path verification, second pass (2026-09-22)

Run after adding `.env` support so that plain `uvicorn app.main:app` picks the file up.

| Check | Result |
|---|---|
| `.env` is read without the `--env-file` flag (placeholder key) | startup log `answer mode: gemini-2.0-flash`; `GET /api/health` -> `llm_available: true` |
| Real outbound HTTPS request to the provider | **PASS** - the provider answered `400 Please pass a valid API key`, i.e. the request left the machine and was understood |
| Behaviour on a rejected key | `POST /api/ask` returned in ~2s with `provider: lexical`, the 3 expected citations, and `note: model unavailable: provider returned 400 ...` - no retry on a permanent 4xx, no failed request, no fabricated prose |
| Behaviour with the key removed | startup log `answer mode: verbatim evidence only (no LLM_API_KEY in .env)`; healthy response with `llm_available: false` |
| `.env` cannot leak into the test suite | `pytest -q` -> **66 passed** both with an empty `.env` and with a key present in it; `tests/conftest.py` clears the key for every test |
| Precedence | a real environment variable overrides `.env` (verified directly against `llm.config()`) |

Still open: one run with a valid key to see generated summary prose and a real citation-guarded answer.
