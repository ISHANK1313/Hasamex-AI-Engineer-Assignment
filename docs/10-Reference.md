# Reference — Ground Truth & Brainstorming Notes

| Field | Value |
|---|---|
| **Document** | Golden dataset + working notes (for thinking/brainstorming) |
| **Version** | v0.1 |
| **Purpose** | Single place to verify accuracy; used by tests and by the demo script |

---

## 1. Source files (case pack)

| File | Expert | Role | Market |
|---|---|---|---|
| `Transcript_1_France.txt` | Dr. Jean Martin | Head of Urology | France |
| `Transcript_2_Germany.txt` | Anna Keller | Former Hospital Procurement Director | Germany |
| `Transcript_3_UK.txt` | Dr. Emily Carter | Consultant Urologist | United Kingdom |

## 2. Transcript stats

| Transcript | Segments (interviewer + expert turns) | Timestamp span |
|---|---|---|
| France | 9 | 00:00 – 06:08 |
| Germany | 9 | 00:00 – 06:05 |
| UK | 10 | 00:00 – 06:04 |

## 3. Interview guide (verbatim)

| # | Question | Topic tag |
|---|---|---|
| Q1 | How would you describe current adoption of robotic surgery in your market? | adoption |
| Q2 | What are the main barriers to adoption? | barriers |
| Q3 | How important are hospital budgets and ROI in purchasing decisions? | cost-roi |
| Q4 | How important are surgeon training and clinical outcomes? | training-outcomes |
| Q5 | What adoption trend do you expect over the next 3–5 years? | growth |
| Q6 | What is the typical hospital decision-making timeline for purchasing a new robotic system? | timeline |

## 4. GOLDEN DATASET — guide answers (used by tests)

Verified by hand from the source text. Quotes are exact substrings.

### Q1 — Current adoption
| Expert | Timestamp | Response kernel (quote anchor) |
|---|---|---|
| France | 00:18 | "Adoption is growing, but it is still concentrated in larger academic hospitals and private centres with stronger capital budgets. Smaller regional hospitals are much slower." |
| Germany | 00:16 | "It is growing, but adoption is quite uneven. Large university hospitals are much more advanced, while many smaller hospitals are still waiting." |
| UK | 00:14 | "Adoption is increasing, and in some larger NHS trusts robotic surgery is becoming standard for selected procedures. But access still varies significantly by hospital." |

### Q2 — Barriers
| Expert | Timestamp | Kernel |
|---|---|---|
| France | 01:20 | "The biggest issue is still capital budget approval… purchasing committees need a strong economic case" |
| Germany | 01:10 | "Cost is the first barrier… The second issue is proving that the system will be used enough." |
| UK | 01:05 | "Funding is important, but I would say training capacity is just as important… if you cannot train enough surgeons and theatre staff, adoption stalls." |

### Q3 — Budgets & ROI
| Expert | Timestamp | Kernel |
|---|---|---|
| France | 02:18 | "Very important… the finance team wants to understand utilisation, procedure volume, maintenance cost and whether the system will actually pay for itself." |
| Germany | 02:08 | "We look at total cost of ownership, expected procedure volume, maintenance, service contracts and training requirements… the economic case decides whether it gets approved." |
| UK | 02:07 / 03:10 | "It matters, but the discussion is not always purely financial… patient outcomes, length of stay, surgeon recruitment…" → "economics and clinical strategy are balanced. I would not say finance alone decides the purchase." |

### Q4 — Training & clinical outcomes
| Expert | Timestamp | Kernel |
|---|---|---|
| France | 03:10 | "Training matters, especially in the first year. If only one surgeon can use the system, the economics become difficult. Hospitals want several surgeons trained so utilisation is high enough." (+ 04:08 outcomes: "necessary, but they are not enough on their own") |
| Germany | 03:05 | "Very important operationally. If the hospital buys a system but only one surgeon is comfortable using it, utilisation will be poor. That weakens the business case." |
| UK | 01:05 / 06:04 | "training capacity is just as important… adoption stalls" → "Hospitals need enough trained people and enough procedure volume to make the programme sustainable." |

### Q5 — 3–5 year trend
| Expert | Timestamp | Kernel |
|---|---|---|
| France | 05:07 | "steady rather than explosive… maybe 15 to 20 percent more procedures annually in some of the stronger centres, but smaller hospitals will remain slower." |
| Germany | 05:08 | "continued growth, but probably closer to high single digits or low double digits in procedure volumes rather than something like 20 percent across the whole market." |
| UK | 04:06 | "adoption could accelerate if training expands and systems become more cost competitive. I could see procedure growth above 15 percent annually in some areas." |

### Q6 — Purchase timeline
| Expert | Timestamp | Kernel |
|---|---|---|
| France | 06:08 | "Six to twelve months is realistic once the hospital becomes serious… longer if the capital committee pushes the purchase into the next budget cycle." |
| Germany | 06:05 | "Nine to eighteen months is common. Procurement, clinical leadership, finance and management all need to align…" |
| UK | 05:04 | "Around six to nine months can happen if funding is already available. If the trust has to wait for a new capital cycle, it can take much longer." |

## 5. GOLDEN DATASET — themes & disagreements (used by tests)

### 5.1 Common themes (agreement across ≥2 experts)
1. **Adoption is growing but uneven** — FR 00:18, GE 00:16, UK 00:14.
2. **Budget/cost/ROI is a central purchase factor** — FR 02:18, GE 02:08, UK 02:07 (with nuance).
3. **Training is critical (single-surgeon risk → poor utilisation)** — FR 03:10, GE 03:05, UK 01:05.
4. **Growth expected to be gradual/steady, not explosive** — FR 05:07, GE 05:08 (UK more optimistic).
5. **Timelines depend on funding/approval cycles** — FR 06:08, GE 06:05, UK 05:04.
6. **Sustainability = trained people + procedure volume** — FR 03:10, GE 03:05, UK 06:04.

### 5.2 Disagreements (contrasting stances)
| Topic | Side A | Side B | Timestamps |
|---|---|---|---|
| **Growth rate (3–5y)** | FR: "15 to 20 percent more procedures annually" (stronger centres) | GE: "high single digits or low double digits… rather than something like 20 percent" | FR 05:07 vs GE 05:08 |
| **Weight of ROI vs clinical in the decision** | FR/GE: "Very important" / "the economic case decides whether it gets approved" | UK: "economics and clinical strategy are balanced. I would not say finance alone decides the purchase." | FR 02:18, GE 02:08 vs UK 03:10 |
| **Primary barrier** | FR/GE: capital budget / cost | UK: training capacity "just as important" (if not #1) | FR 01:20, GE 01:10 vs UK 01:05 |
| **Timeline length** | FR: 6–12 months; UK: 6–9 months (funding ready) | GE: 9–18 months common | FR 06:08, UK 05:04 vs GE 06:05 |

> UK is the interesting outlier on almost every axis — good demo talking point. GE is the most
> procurement/economics-driven; FR stands between; UK is the most clinically/strategically balanced.

## 6. Brainstorm / thinking notes (why this design)

- **The case's silent requirement is trust.** Not "smart answers" — *defensible* answers. So the
  architecture leads with citation integrity, not model cleverness.
- **Exact quotes** imply we must never paraphrase **inside a quote**. Code does extraction; the LLM is
  confined to summaries over those quotes. This is the cleanest division of labour.
- **Timestamps exist in the source** (`MM:SS`). Keeping them attached to segments is a *parse* problem,
  not an AI problem. Don't ask the model for timestamps it could invent; carry them in the data.
- **Themes/disagreements** can be deterministic on 3 experts because the guide questions map 1:1 to
  topics. For 30+ experts, upgrade to embedding clustering (same citation layer).
- **"Ask questions"** = retrieval + grounded synthesis. Lexical BM25 is enough for 3 short docs and is
  the honest no-key demo; embedding hybrid is the scale answer.
- **Video story arc:** show a claim → show its quote → show its timestamp → show the verification test.
  That covers "accuracy" and "explainability" in one demo.

## 7. Decisions log (kept as we build)

| # | Date | Decision | Rationale |
|---|---|---|---|
| D1 | 2026-09-21 | Deterministic extraction first, LLM last | anti-hallucination + testable accuracy |
| D2 | 2026-09-21 | Exact-substring quote check | "exact quotes" requirement is a hard test |
| D3 | 2026-09-21 | SQLite+FTS5 baseline | offline demo, zero install, honest scale story |
| D4 | 2026-09-21 | No-key default; LLM opt-in via `.env` | panel may not provide keys |
| D5 | 2026-09-21 | Stack pending Phase 0 (Python recommended) | fastest demo, best AI ecosystem |
| D6 | 2026-09-21 | qa_log persisted | demo evidence + cheap answer cache |
| D7 | 2026-09-21 | Golden dataset as regression tests | "accuracy" becomes checkable, not vibes |

## 8. Open questions

- Will the panel environment have internet+API keys for the live demo? → demo in no-key (lexical) mode,
  LLM as secondary path.
- Preferred stack? → Phase 0 question.
- Should quotes be sentence-length or minimal? → default: sentence-length for readability; both easy.
- Any expectation to handle audio/video? → brief says text transcripts; out of scope, mentioned.