# Demo Script — Video walkthrough (follow this when recording)

| Field | Value |
|---|---|
| **Document** | Word-for-word-ish demo script (~8–10 min) |
| **Related** | [11-Checklist](11-Checklist.md) §E, [12-Fast-Lookup](12-Fast-Lookup.md) §3–4 |
| **Tip** | Screen record; show the app and the terminal (pytest). Speak to the *requirements*, not just the UI. |

---

## 0:00 – 0:30 · Intro
> "This is an expert-call transcript analyser for the European Robotic Surgery case. It reads the three
> sample transcripts, answers each question in the interview guide for every expert, extracts exact
> quotes with timestamps, finds common themes and disagreements across the three calls, and lets you ask
> questions across all the transcripts. The core idea: **every claim on screen is traceable to a verbatim
> quote and a timestamp in the source file.**"

## 0:30 – 1:30 · Loading & parsing
> "The app pre-loads the three transcripts — France, Germany, UK. Behind the scenes, parsing is
> **deterministic**: a regex-based parser splits each file into speaker turns with start and end timestamps,
> and stores them as segments in SQLite." *(Click "transcripts" / show list.)*
> "No AI is involved in parsing or timestamps — those come straight from the file. That's the first
> hallucination control."

## 1:30 – 3:00 · Guide answers
> "Here's the interview guide: six questions. For each question you see one row per expert — a short
> summary, the **exact quote**, and the **timestamp** it came from."
> *(Demo Q1 — adoption: FR 00:18, GE 00:16, UK 00:14.)*
> "Note the quotes are verbatim — literally copied from the transcript. The matcher is a deterministic
> scorer; the summariser only writes prose over the evidence I show you."

## 3:00 – 4:00 · Themes & disagreements
> "Across the three calls, common themes: adoption is growing but uneven; budget and ROI dominate
> purchasing; training is critical; growth is steady, not explosive."
> *(Show the theme cards.)*
> "And here are the disagreements — this is where it gets interesting:
> - **Growth:** France expects 15–20% a year; Germany says high single to low double digits, *not* 20% across the market.
> - **ROI:** German and French experts say the economic case decides; the UK expert says finance alone does not decide — it's balanced with clinical strategy.
> - **Top barrier:** France/Germany say capital budget and cost; the UK expert says training capacity is just as important.
> Every point links back to its quotes and timestamps."

## 4:00 – 5:00 · Ask questions
> *(Typing: "How long does purchasing a robotic system take?")*
> "I asked a question across all transcripts. The system retrieved the relevant segments — France 6–12
> months, Germany 9–18 months, UK 6–9 months when funding is ready — and every sentence in the answer is
> cited with speaker and timestamp. No citation, no claim."

## 5:00 – 6:30 · Hallucination controls
> "Three layers. **One:** quotes are extracted by code as exact substrings; the model never writes a quote.
> **Two:** if an optional LLM is used, it sees only the retrieved evidence, and after generation the app
> checks that every timestamp it cited actually exists in that evidence — otherwise it falls back.
> **Three:** if there's no evidence, the app says 'insufficient evidence' instead of guessing.
> And there's a **no-key mode**: *(unset .env / show)* without any API key the app still answers, using the
> same cited verbatim snippets — perfect for an offline demo."

## 6:30 – 8:00 · Scaling 3 → 30+
> "Nothing in the architecture depends on having three transcripts. To go to 30+ I'd: keep the same
> parser and citation layer; swap the FTS5-only index for a **hybrid BM25 + vector index**; replace the
> lexicon-based theme classification with **embedding clustering** (HDBSCAN); ingest in parallel; and move
> from SQLite to Postgres with pgvector. The API and the UI stay the same."

## 8:00 – 9:00 · Accuracy proof (terminal)
> "Because accuracy is the core requirement, I encoded the expected answers into a **golden dataset** and
> the test suite verifies all 18 expected answers, the themes, and the disagreements — plus a test that
> every single quote is an exact substring of its source. *(Run `pytest` — green.)* The claims are
> mechanically verifiable, not just vibes."

## 9:00 – 10:00 · Wrap-up
> "Stack: Python, FastAPI, SQLite FTS5, a single-page frontend, and an optional LLM adapter (OpenAI-compatible,
> default off). Decisions I'd highlight: deterministic extraction first, LLM last; timestamp-true citations;
> exact-substring quotes; no-key fallback. If I had more time I'd add PDF export of findings and an
> embedding-based theme map. Thank you."

---

## Extra: 3 demo questions to practise

| Question | Expected cited answer (timestamps) |
|---|---|
| "How long does purchasing take?" | FR 06:08, GE 06:05, UK 05:04 |
| "What's the main barrier?" | FR 01:20, GE 01:10, UK 01:05 (training) |
| "Is growth going to be fast?" | FR 05:07, GE 05:08, UK 04:06 |