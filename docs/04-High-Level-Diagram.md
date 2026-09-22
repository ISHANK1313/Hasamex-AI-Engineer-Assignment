# High-Level Diagram (C4 Level 1–2)

| Field | Value |
|---|---|
| **Document** | High-Level / Container Diagram |
| **Version** | v0.1 |
| **Related docs** | [03-Architecture](03-Architecture.md), [05-Low-Level-Diagram](05-Low-Level-Diagram.md) |

---

## 1. System Context (C4 Level 1)

```
                    ┌──────────────────────────────┐
                    │     Research Analyst (User)  │
                    │  (evaluator & end user)      │
                    └──────────────┬───────────────┘
                                   │ opens browser
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Expert-Call Transcript Analyzer                    │
│           "Analyses expert calls, answers guide, cites everything"   │
│                                                                      │
│  • Load 3 sample transcripts            • Answers interview guide    │
│  • Exact quotes + timestamps             • Themes & disagreements    │
│  • Ask questions across all calls        • Optional LLM synthesis    │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ reads
                           ▼
                  ┌────────────────┐        ┌───────────────────────────┐
                  │ sample data    │        │ OpenAI-compatible LLM API │
                  │ *Transcript_1_ │        │ (OPTIONAL — no-key mode   │
                  │  France.txt    │        │  works without it)        │
                  │ *Transcript_2_ │        └───────────────────────────┘
                  │  Germany.txt   │
                  │ *Transcript_3_ │
                  │  UK.txt        │
                  └────────────────┘
```

## 2. Containers (C4 Level 2)

```
┌──────────┐   HTTP/JSON   ┌──────────────────────────────────────────────────────────┐
│ Browser  │◄─────────────►│  Web App + API  (FastAPI, port 8000)                       │
│ (SPA)    │               │                                                            │
└──────────┘               │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐  │
                           │  │ API layer    │ │ Service layer│ │ Storage layer      │  │
                           │  │ /api routes  │►│ guide/themes │►│ SQLite + FTS5      │  │
                           │  └──────────────┘ │ /ask/quote   │ │ data.db            │  │
                           │                   └──────┬───────┘ └────────────────────┘  │
                           │                          │                                 │
                           │                    ┌─────▼─────┐  ┌─────────────────────┐  │
                           │                    │ Ingestion │  │ LLM adapter (opt.)  │  │
                           │                    │ parser    │  │ openai-compatible   │  │
                           │                    └───────────┘  └─────────────────────┘  │
                           │        serves static/ (index.html, app.js, style.css)      │
                           └──────────────────────────────────────────────────────────┘
```

## 3. Data Flow (one-line view)

```
Transcripts ──► Parser ──► Segments(+timestamps) ──► SQLite
                    │
                    ├─► Guide matcher ──► Answers + verbatim quotes ──► UI
                    ├─► Topic cluster ──► Themes / Disagreements ────► UI
                    └─► FTS5 index ──► Retrieval ──► (LLM?) ──► Cited answer ──► UI
```

## 4. Deployment (local demo)

```
Single machine:
  FastAPI (uvicorn) 0.0.0.0:8000
    ├─ serves SPA  → http://localhost:8000
    ├─ serves API  → http://localhost:8000/api/*
    ├─ data.db (SQLite, created on first run)
    └─ optional outbound HTTPS → LLM provider (only if .env has API key)
```

## 5. NFR mapping

| NFR | Where it shows in this diagram |
|---|---|
| Traceability | Service layer keeps `segment_id` through answers/quotes/retrieval |
| No fabrication | All LLM calls bounded by evidence pack from Storage |
| Simplicity | 1 process, 2 run commands, SPA served by same server |
| Scalability | Storage/Service/API separation = drop-in stronger DB/index later |