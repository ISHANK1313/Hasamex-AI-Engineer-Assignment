# Low-Level Diagram (C4 Level 3 — component/class level, no-UML)

| Field | Value |
|---|---|
| **Document** | Low-Level Diagram |
| **Version** | v0.1 |
| **Related docs** | [03-Architecture](03-Architecture.md), [06-Request-Flow](06-Request-Flow.md), [07-Database-Schema](07-Database-Schema.md) |

---

## 1. Module / Package Layout (Python reference)

```
app/
├── main.py                      # FastAPI app, static mount, startup ingest
├── api/
│   ├── routes_transcripts.py    # GET /transcripts, POST /transcripts/ingest
│   ├── routes_guide.py          # GET /guide-answers
│   ├── routes_themes.py         # GET /themes
│   └── routes_ask.py            # POST /ask
├── models/
│   ├── transcript.py            # Transcript, Expert, Segment (pydantic)
│   ├── answer.py                # GuideAnswer, Quote, Theme, Disagreement, AskResponse
│   └── dtos.py                  # request/response DTOs
├── ingest/
│   ├── parser.py                # parse_transcript(text) -> ParsedTranscript
│   ├── header_parser.py         # expert/role/market from header lines
│   └── line_parser.py           # regex → segment; end_time estimation
├── services/
│   ├── guide_service.py         # QuestionMatcher + answer assembly
│   ├── theme_service.py         # topic clustering → themes/disagreements
│   ├── quote_service.py         # QuoteExtractor (exact substring)
│   └── qa_service.py            # retrieval + (LLM) synthesis + citation check
├── llm/
│   ├── gateway.py               # LLMClient protocol: complete(messages) -> str
│   ├── openai_gateway.py        # OpenAI-compatible impl (key from env)
│   └── prompts.py               # GUIDE_SUMMARY_PROMPT, QA_SYSTEM_PROMPT, citation rules
├── storage/
│   ├── db.py                    # sqlite3 connection mgmt, schema migration v1
│   ├── segment_repo.py          # upsert transcripts/segments, get by id/expert
│   ├── guide_repo.py            # save/load guide answers + quotes
│   ├── theme_repo.py            # save/load themes + theme_items
│   ├── qa_repo.py               # qa_log
│   └── search.py                # FTS5 index build/query (BM25)
└── static/
    ├── index.html               # 3 tabs: Guide | Themes | Ask (+ Upload)
    ├── app.js                   # fetch API, render, copy-quote buttons
    └── style.css                # minimal clean styling
tests/
├── test_parser.py
├── test_matcher.py              # golden: 6 questions × 3 experts
├── test_quotes.py               # verbatim integrity
├── test_themes.py               # golden themes/disagreements
├── test_api.py                  # integration: ingest→guide→themes→ask
└── test_nokey.py                # /ask without LLM
data/
├── transcripts/                 # the 3 sample .txt files (also bundled)
└── golden_dataset.json          # expected answers/timestamps/themes (tests)
```

## 1a. Implementation note (v1 as shipped)

The module tree below is the target shape, kept because it is the honest 30+ transcript story. The
shipped v1 collapses it to `app/analyze.py` (parser + matcher + quotes + themes + retrieval),
`app/llm.py` (optional model layer) and `app/main.py` (routes + in-memory store), with no SQLite and
no repository. The class contracts in §2 are unchanged and live in those three files; every sequence
in §3-§6 runs as drawn, with the store holding three parsed transcripts instead of a database
([adr/0001](adr/0001-in-memory-store.md)).

## 2. Key Classes & Responsibilities

### 2.1 `Segment`
```
Segment
├── id: int
├── transcript_id: int          # FK → transcripts
├── expert: str
├── speaker: str                # Interviewer | Dr. Martin | Anna Keller | ...
├── role: str | None            # e.g. Head of Urology
├── start_time_s: int
├── end_time_s: int
├── text: str
└── raw_line: int               # source line for debugging
```
Notes: `end_time_s` = next segment start; last segment = start + 18s (estimate). Timestamps render `MM:SS`. Exposed globally by `services/quote_service`.

### 2.2 `QuestionMatcher`
```
QuestionMatcher
├── lexicon: dict[question_id, set[str]]     # per-question keyword/synonym set
└── match(question, segments) -> Ranked[]    # weighted term frequency + phrase overlap
    rules: min_score threshold → "Not covered" if none above
```
### 2.3 `QuoteExtractor`
```
QuoteExtractor
└── extract(segment, span) -> Quote
    • takes a numeric position (from matcher) or text slice
    • expands to sentence boundaries
    • asserts segment.text.contains(quote)  ← exact-substring integrity
    • returns Quote {text, start_char, end_char, segment_id, timestamp}
```
### 2.4 `ThemeService`
```
ThemeService
├── TOPICS: dict[str, set[str]]   # adoption, cost/roi, training, outcomes, timeline, growth
├── POLARITY: dict[str, 1|-1]     # accelerate=+1, gradual=-1, etc. (for disagreements)
└── compute(segments) -> (themes[], disagreements[])
    theme        = topic with segments from ≥2 experts
    disagreement = topic where expert stances differ (opposing polarity or
                   numeric value gaps, e.g. growth ~15-20% vs high-single/low-double digits)
```
### 2.5 `QAService`
```
QAService
├── retrieve(question, k) -> Segment[]        # FTS5 BM25 (+embeddings if key)
├── build_evidence(segments) -> str           # "01:20 Dr. Martin: <verbatim> ..."
├── synthesize(evidence, question) -> str     # LLM (opt.) with citation instructions
├── check_citations(answer, evidence) -> bool # every [MM:SS] in answer ∈ evidence timestamps
└── respond(...) -> AskResponse               # no-key → verbatim snippets fallback
```

## 3. Sequence: Startup ingest

```
main.py ──► db.init_schema()
main.py ──► ingest.load_bundled("data/transcripts/*.txt")
   parser.parse_transcript(text)
     header_parser → expert/role/market
     line_parser   → segments (regex ^MM:SS speaker: text)
     validator     → errors? → log + 422 (only for uploads)
segment_repo.upsert(transcript, segments)
search.rebuild_index("segments", "fts_segments")
```

## 4. Sequence: Guide answers for all experts

```
GET /api/guide-answers
   guide_service.all_answers()
     for q in guide_questions:
        for expert in experts:
           segs = segment_repo.by_expert(expert)
           top  = matcher.match(q, segs, k=2)
           if not top → answer(not_covered=True)
           quotes = [quote_extractor.extract(s) for s in top]
           summary = llm? summarize(evidence=quotes) : join(quote snippets)
           guide_repo.upsert(guide_answer, quotes)
   → json grouped {question → {expert → {summary, quotes[{text, timestamp}]}}}
```

## 5. Sequence: Themes & disagreements

```
GET /api/themes
   theme_service.compute(all_segments)
     topic buckets via TOPICS lexicon + segment overlap
     for topic, segs:
        if distinct_experts(segs) >= 2 → theme item (quotes per expert)
        if stance clash detected        → disagreement item (side A/B quotes)
   → {themes: [{topic, summary, experts, quotes[]}],
      disagreements: [{topic, claim_a, claim_b, quotes_a[], quotes_b[]}]}
```

## 6. Sequence: Ask

```
POST /api/ask {question, top_k=4, use_llm=true}
   qa_service.respond(...)
     segs = retrieve(question, top_k)         # BM25; k n/a when corpus tiny? keep 4
     ev   = build_evidence(segs)
     if use_llm and key:
        ans = llm.complete(system=QA_SYSTEM_PROMPT, user=ev + question)
        if not check_citations(ans, ev):         # [MM:SS] must exist in evidence
            ans = fallback(ans, ev)              # strip citations → re-answer low-temp
     else:
        ans = verbatim_snippets(segs)            # deterministic, always cited
     qa_repo.log(question, ans, seg_ids)
   → {answer, citations:[{speaker, timestamp, text, transcript}]}
```

## 7. Error paths

| Where | Condition | Behaviour |
|---|---|---|
| upload | malformed line | 422 `{line_no, reason}`; skip file, keep samples |
| matcher | no segment above threshold | answer `not_covered: true` |
| LLM | no key / timeout / bad JSON | service returns lexical fallback + `provider:"lexical"` |
| citation check | hallucinated timestamp | fallback path re-answers, evidence-only *(logged)* |
| FTS5 | query returns 0 | Q&A returns `{answer:"insufficient evidence", citations:[]}` |

## 8. Golden dataset wiring

- `data/golden_dataset.json` mirrors Reference §4/§5; tests load it and assert:
  - exact expected timestamps per guide answer (e.g., France Q1 → `00:18`, Q8→`06:08`)
  - themes list contains [adoption-uneven, budget/ROI-primary, training-matters]
  - disagreements contain [growth rate, ROI vs clinical balance, timeline range, training-as-#1-barrier-in-UK]