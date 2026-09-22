# Request Flow — End-to-End Walkthroughs

| Field | Value |
|---|---|
| **Document** | Request Flow / Sequence walkthroughs |
| **Version** | v0.1 |
| **Related docs** | [03-Architecture](03-Architecture.md), [05-Low-Level-Diagram](05-Low-Level-Diagram.md) |

---

## Flow 0 — App startup (loads samples)

```
User runs: uvicorn app.main:app --reload
   │
   ▼
main.py
   ├─ init_schema()                     → creates data.db tables if absent
   ├─ load_bundled("data/transcripts")  → parses 3 transcripts (≈9 segs each)
   └─ search.rebuild_index()            → FTS5 populated
   │
   ▼
Browser http://localhost:8000  →  SPA loads → GET /api/transcripts
Response: [{id, expert:"Dr. Jean Martin", market:"France", segments:9}, …]
```

## Flow 1 — Guide answers (per expert, with quotes + timestamps)

```
Browser ──► GET /api/guide-answers

guide_service.all_answers()
  Q1 "How would you describe current adoption...?"
    France  → matcher top: Seg@00:18 text "Adoption is growing, but it is still
              concentrated in larger academic hospitals and private centres..."
              quote = exact substring, timestamp = 00:18
    Germany → Seg@00:16 "growing, but adoption is quite uneven..."
    UK      → Seg@00:14 "increasing, and in some larger NHS trusts... standard
              for selected procedures... varies significantly by hospital"
  ... (Q2..Q6 same pattern)

Response:
{ questions: [
    { id:1, text:"...adoption...",
      answers: [
        { expert:"France", confidence:0.9, not_covered:false,
          summary:"Adoption is growing but uneven; concentrated in academic/large centres.",
          quotes:[ {"text":"Adoption is growing, but it is still concentrated in larger academic hospitals...",
                    "timestamp":"00:18","speaker":"Dr. Martin"} ] },
        ...
      ]},
  ...]}

Rendering (SPA):
  For each guide question → table row per expert:
    | Expert | Summary | Exact quote (highlight) | ⏱ 00:18 | [link to segment] |
```

## Flow 2 — Themes & disagreements

```
Browser ──► GET /api/themes

theme_service.compute(all_segments)
  1. bucket segments by topic lexicon:
     - "adoption" (Q1/Q5 segs)
     - "budget cost ROI" (Q2/Q3 segs)
     - "training" (Q4 segs)
     - "timeline" (Q6 segs)
  2. ≥2 experts in bucket → THEME
     e.g. TRAINING: explicit in FR (03:10), GE (03:05), UK (01:05 + 06:04)
     → theme {topic:"training", experts:[FR,GE,UK], quotes:[3]}
  3. contrast detection → DISAGREEMENT
     e.g. GROWTH RATE: FR "15-20%" (05:07) vs GE "high single digits or low double" (05:08)
           ROI weight: FR "Very important" (02:18) / GE "decides whether it gets approved" (02:08)
                       vs UK "economics and clinical strategy are balanced" (03:10)
     → disagreement {topic:"growth-rate", claim_a:"…15 to 20 percent more…"(FR), claim_b:"…closer to high single digits…"(GE)}

Response: {themes:[...], disagreements:[...]}   // each with quotes+timestamps
```

## Flow 3 — Free-form question (cross-transcript, cited)

```
Browser ──► POST /api/ask
  body: {"question":"How long does purchasing a robot typically take?",
         "top_k":4,"use_llm":true}

qa_service.respond():
  1. retrieve("how long purchase robot take")
     FTS5 BM25 top hits:
       FR seg 06:08 "Six to twelve months is realistic once the hospital becomes serious. …"
       GE seg 06:05 "Nine to eighteen months is common. Procurement, clinical leadership, finance…"
       UK seg 05:04 "Around six to nine months can happen if funding is already available. …"
       FR seg 01:20 "capital budget approval…" (lower score, may be cut at k)
  2. evidence pack = "06:08 Dr. Jean Martin: Six to twelve months…\n06:05 Anna Keller: Nine to eighteen months…\n01:20 Dr. Jean Martin: …"
  3. LLM (if key): system="Answer ONLY from the evidence. Cite [MM:SS, Speaker] after each claim…"
     → "Purchase timelines vary: six to twelve months in France [06:08, Dr. Jean Martin],
        nine to eighteen months in Germany [06:05, Anna Keller], and six to nine months
        in the UK when funding is available [05:04, Dr. Emily Carter]."
  4. citation check: every [MM:SS] ∈ {06:08, 06:05, 05:04} ✓
  5. no key → answer = verbatim snippets list (same citations) with provider:"lexical"

Response:
{ answer:"…", provider:"openai"|"lexical",
  citations:[
    {"speaker":"Dr. Jean Martin","timestamp":"06:08","text":"Six to twelve months is realistic…","transcript":"France"},
    {"speaker":"Anna Keller","timestamp":"06:05","text":"Nine to eighteen months is common…","transcript":"Germany"},
    {"speaker":"Dr. Emily Carter","timestamp":"05:04","text":"Around six to nine months can happen…","transcript":"UK"}
  ]}
```

## Flow 4 — Upload a custom transcript

```
Browser ──► POST /api/transcripts/ingest (multipart file)

parser.parse_transcript(upload) → ParsedTranscript | raises ParseError
  on ParseError → 422 {"line_no":12,"reason":"missing timestamp"}  (UI shows error banner)
success → segment_repo.upsert + search.rebuild_index (incremental FTS5)
Response: {"ingested":[{"expert":"Expert 4 – …","segments":N}]}
UI: new expert appears in Guide + Themes + Ask dropdowns
```

## Failure/safety paths (same as LLD §7)

| Case | User impact | Safety net |
|---|---|---|
| No API key / LLM down | Answers appear as verbatim cited snippets | lexical fallback, provider field |
| LLM invents a timestamp | Citation check fails | fallback re-answers from evidence; logged |
| Question with no evidence | "Insufficient evidence; closest snippets:" | threshold check before synthesis |
| Malformed upload | 422 with line number | samples remain; app still usable |