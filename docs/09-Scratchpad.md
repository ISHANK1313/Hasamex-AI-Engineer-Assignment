# Scratchpad — Running Thoughts

| Field | Value |
|---|---|
| **Document** | Scratch pad (not for submission; keep for yourself) |
| **Related** | [10-Reference](10-Reference.md) (ground truth), [08-Phases](08-Phases.md) |

---

## 1. First read of the case (what jumped out)

- "Build a **simple** application" — they're testing restraint, not complexity. A bloated app would be a red flag.
- "**Do not invent information**" — this is THE core requirement. Everything else hangs off traceability.
- "Show the **source timestamp** for each answer/quote" — timestamps are data, not model output.
- They will ask in the demo about **architecture, model choice, citations, hallucination reduction, and scaling to 30+**. The app matters, but so does the 10-minute story.

## 2. Core insight (the "aha")

> If extraction is **deterministic** (parser + matcher + exact-substring quotes) and the LLM is only
> allowed to summarise over retrieved evidence, then *hallucination is structurally impossible for the
> two hardest requirements* (quotes and timestamps). The LLM never produces a quote or a timestamp —
> it only emits prose alongside quotes the code extracted and verified.

This single decision answers 4 of the 5 demo questions at once.

## 3. Features → techniques mapping

| Requirement | Technique (v1) | Scale (30+) |
|---|---|---|
| Load transcripts | bundled files + optional upload | same parser, parallel ingest |
| Guide answers | lexicon scorer per question | keep (or supervised classifier) |
| Exact quotes | substring integrity check | same |
| Timestamps | carried in segment object from parse | same |
| Themes/disagreements | topic buckets + polarity | embedding clustering (HDBSCAN) |
| Ask questions | FTS5 BM25 + optional LLM over evidence | hybrid retrieval + rerank + caching |

## 4. Numbers I should be able to quote in the demo

- 3 experts · 6 guide questions · 18 expected answers · 0 invented quotes.
- Transcript sizes: France 9 turns, Germany 9 turns, UK 10 turns; all under ~7 min.
- Index: one FTS5 table, ~28 rows of segments total.
- Q&A latency target: < 5s with LLM, instant lexical.

## 5. Demo narratives to rehearse

1. **The traceability demo:** click Q1 → France answer → click the quote → shows source line + timestamp.
2. **The disagreement demo:** growth-rate — FR "15–20%" vs GE "high single digits" vs UK "above 15% in areas".
3. **The trust demo:** turn off the API key → app still answers with verbatim snippets (lexical mode).
4. **The scale demo:** "I didn't change architecture to go from 3 to 30; I'd turn on embeddings + clustering and use a real DB."
5. **The test demo:** run `pytest` — golden dataset proves accuracy mechanically.

## 6. Pitfalls to avoid

- ❌ Ask the LLM to "extract quotes" — it will paraphrase or invent.
- ❌ Let the LLM emit timestamps — it has no idea.
- ❌ Build a chat UI that implies the bot knows anything outside the transcripts.
- ❌ Hard-code answers to look good — golden tests must come from the real transcript text.
- ❌ Over-engineering v1 (auth, Docker, k8s) — it just slows the demo.

## 7. Priorities if time gets short (build order)

1. Parser + segment model + FTS5 (everything depends on this).
2. Guide answers with quotes + timestamps (the core ask).
3. Q&A lexical mode (works offline).
4. Themes/disagreements (algorithmic).
5. UI (single page, three tabs).
6. LLM gate + citation checks (optional polish).
7. Video + README + submit.

## 8. Ideas parked for later (do NOT build in v1)

- Audio transcription (whisper) — the case gives text.
- PDF/CSV export of findings.
- Multi-project workspaces, user accounts.
- Chat history (deliberately excluded — see Memory doc).