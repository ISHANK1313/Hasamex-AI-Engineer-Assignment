"""Deterministic core: parsing, evidence selection, verbatim quotes, themes, disagreements, retrieval.

No LLM in this module on purpose. Quotes must be exact substrings and timestamps must come from the
file, so the trust layer is plain code that tests can pin down.

Key structural insight the rest of this file leans on: the transcripts are strictly paired. Every
interviewer turn is (a paraphrase of) an interview-guide question, and the turn right after it is
that expert's answer. So routing a guide question to an expert's answer is a lookup, not a guess.
Keyword scoring over the whole transcript was tried first and reliably picked the wrong turn
(e.g. an ROI turn as the answer about training); the pairing is what makes extraction accurate.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# --- parsing ---------------------------------------------------------------------------------

# Transcript layout:
#   Expert 1 - Dr. Jean Martin      <- no colon, so it needs its own pattern (dash may be en/em)
#   Role: Head of Urology
#   Market: France
#
#   00:18                           <- timestamp on its own line
#   Dr. Martin: Adoption is growing...
_TS_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
_HEADER_RE = re.compile(r"^([^:]+):\s*(.+)$")
_EXPERT_RE = re.compile(r"^expert\s*\d*\s*[\u2013\u2014-]\s*(.+)$", re.I)


def _mmss(seconds: int) -> str:
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def parse_transcript(text: str, source: str = "") -> dict:
    """Return {expert, role, market, source, segments[]}. Raises ValueError on malformed input."""
    # Notepad and PowerShell write UTF-8 with a BOM by default; without this the first header line
    # becomes "\ufeffExpert 1 - ..." and the upload fails with a confusing message.
    text = text.lstrip("\ufeff")
    expert = role = market = ""
    segments: list[dict] = []
    pending_ts: int | None = None

    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue

        if m := _TS_RE.match(line):
            pending_ts = int(m.group(1)) * 60 + int(m.group(2))
            continue

        # Header block: recognised by a timestamp not yet having been seen.
        if pending_ts is None:
            if em := _EXPERT_RE.match(line):
                expert = em.group(1).strip()
                continue
            if head := _HEADER_RE.match(line):
                key, value = head.group(1).strip().lower(), head.group(2).strip()
                if key == "role":
                    role = value
                elif key == "market":
                    market = value
                elif key.startswith("expert"):
                    expert = value
                continue
            raise ValueError(f"{source}:{i}: unexpected line in header: {line!r}")

        if head := _HEADER_RE.match(line):  # a dialogue turn
            segments.append({"speaker": head.group(1).strip(), "start_s": pending_ts, "text": head.group(2).strip()})
            pending_ts = None
            continue

        if segments:  # continuation of the previous turn
            segments[-1]["text"] += " " + line
            continue
        raise ValueError(f"{source}:{i}: unexpected line after a timestamp: {line!r}")

    if pending_ts is not None:
        raise ValueError(f"{source}: trailing timestamp with no dialogue line: {_mmss(pending_ts)}")
    if not segments:
        raise ValueError(f"{source}: no dialogue turns found")

    market = market or source
    for s in segments:
        s["timestamp"] = _mmss(s["start_s"])
        s["id"] = f"{market}:{s['timestamp']}:{s['speaker']}"
        s["market"] = market
        s["is_expert"] = "interviewer" not in s["speaker"].lower()

    return {"expert": expert, "role": role, "market": market, "source": source, "segments": segments}


def load_transcripts(directory: Path | None = None) -> list[dict]:
    directory = directory or DATA / "transcripts"
    out = [parse_transcript(p.read_text(encoding="utf-8"), p.name) for p in sorted(directory.glob("*.txt"))]
    if not out:
        raise ValueError(f"no transcripts found in {directory}")
    return out


def pairs(transcript: dict) -> list[dict]:
    """Interviewer turn -> the expert turn that answers it. The transcript's own structure."""
    segs = transcript["segments"]
    out = []
    for i, s in enumerate(segs):
        if s["is_expert"]:
            continue
        answer = segs[i + 1] if i + 1 < len(segs) and segs[i + 1]["is_expert"] else None
        out.append({"question": s, "answer": answer})
    return out


# --- guide questions -------------------------------------------------------------------------

# Topic order maps to the numbered questions in the interview guide.
TOPICS = [
    ("adoption", "Adoption"),
    ("barriers", "Barriers"),
    ("cost_roi", "Budgets and ROI"),
    ("training_outcomes", "Training and outcomes"),
    ("growth", "Growth outlook"),
    ("timeline", "Purchase timeline"),
]

# Terms that mark a turn as being about a topic. Matched as lowercase word prefixes, so "purchas"
# covers purchase/purchasing and "train" covers train/trained/training.
TOPIC_TERMS: dict[str, list[str]] = {
    "adoption": ["adopt", "grow", "increas", "uneven", "concentrat", "advanc", "standard", "vari", "access"],
    "barriers": ["barrier", "issue", "fund", "budget", "approv", "capital", "capacity", "stall",
                 "priorit", "pressure", "cost", "hold back", "block", "holding"],
    "cost_roi": ["roi", "econom", "financ", "pay for itself", "total cost of ownership", "utilis",
                 "utiliz", "very important", "decid", "volume", "maintenance", "matters"],
    "training_outcomes": ["train", "surgeon", "outcome", "clinic", "comfortab", "staff", "theatre", "sustain"],
    "growth": ["expect", "accelerat", "gradual", "steadi", "explosiv", "percent", "single digits",
               "double digits", "outlook", "growth", "procedur", "annual"],
    "timeline": ["month", "timeline", "committe", "budget cycle", "capital cycle", "wait", "longer", "align"],
}

# Extra cues that only appear in a *question* ("So ROI is important?"). Question text is short, so
# this is where the intent actually lives.
QUESTION_CUES: dict[str, list[str]] = {
    "adoption": ["adoption", "describe"],
    "barriers": ["barrier", "holding", "hold back", "blocking"],
    "cost_roi": ["roi", "budget", "economics", "economic", "finance", "financial", "pay for"],
    "training_outcomes": ["training", "outcomes", "clinical"],
    "growth": ["outlook", "three to five", "3-5", "next three", "next 3", "accelerate", "expect"],
    "timeline": ["timeline", "how long", "how soon", "decision-making", "decision making"],
}

# Cues in a *user's* free-form question that route it to a guide topic before searching.
# Longest matching cue wins, so "main barrier" beats the "adoption" in "the main barrier to adoption".
TOPIC_CUES: dict[str, list[str]] = {
    "adoption": ["how widespread", "how common", "current state", "mature", "penetration", "how adopted",
                 "adoption", "adopted"],
    "barriers": ["main barrier", "barriers to", "barrier to", "barrier", "hold back", "blocking",
                 "obstacle", "why slow", "challenge", "problem", "stopping", "holding"],
    "cost_roi": ["roi", "budget", "cost", "expensive", "afford", "economic", "financial", "pay for",
                 "finances", "finance", "price"],
    "training_outcomes": ["training", "train", "surgeon skill", "learning curve", "outcome", "clinical", "staff"],
    "growth": ["next three", "next 3", "next five", "next 5", "3-5", "5 years", "three to five",
               "future", "outlook", "trend", "expect", "growth", "grow", "accelerate", "fast"],
    "timeline": ["how long", "how soon", "how many months", "timeline", "duration", "decision-making",
                 "decision making", "how quickly", "take to buy", "lead time"],
}


def load_guide(path: Path | None = None) -> list[dict]:
    """Parse the numbered questions out of the interview guide, in order."""
    path = path or DATA / "Interview_Guide.txt"
    questions = re.findall(r"^\s*(\d+)\.\s+(.+?)\s*$", path.read_text(encoding="utf-8"), re.M)
    if len(questions) != len(TOPICS):
        raise ValueError(f"expected {len(TOPICS)} guide questions, found {len(questions)}")
    return [
        {"id": int(num), "topic": topic, "name": name, "question": text}
        for (num, text), (topic, name) in zip(questions, TOPICS)
    ]


# --- matching and quotes ---------------------------------------------------------------------

def _term_hits(text: str, topic: str) -> int:
    low = text.lower()
    return sum(1 for term in TOPIC_TERMS[topic] if re.search(rf"\b{re.escape(term)}", low))


def _question_hits(text: str, topic: str) -> int:
    low = text.lower()
    return sum(1 for cue in QUESTION_CUES[topic] if cue in low)


def _asked_about(text: str, topic: str) -> bool:
    """The interviewer's question is about this topic and about no other topic at least as much.

    Only the extra pairs are gated on this. The barriers question here is "What is holding adoption
    back?", so a second *adoption* quote was being built from the barriers answer: real quote, wrong
    label. A question that names two topics belongs to the stronger one.
    """
    own = _question_hits(text, topic)
    return own > 0 and all(_question_hits(text, t) < own for t, _ in TOPICS if t != topic)


def sentences(text: str) -> list[str]:
    return [p for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p]


def best_quote(segment: dict, topic: str) -> str:
    """The contiguous run of sentences carrying the topic's evidence. Verbatim by construction.

    A span rather than a single sentence: an expert's answer usually spans two sentences, and
    taking only the highest-scoring one silently dropped the half that held the number.
    """
    sent = sentences(segment["text"])
    scored = [i for i, s in enumerate(sent) if _term_hits(s, topic)]
    if not scored:
        return segment["text"]
    start, end = scored[0], scored[-1]
    # A short opener carries the verdict while the evidence sits in the next sentence
    # ("Very important. The clinical argument may get surgeons interested, but ...").
    # Without it the quote reads as a non-answer.
    if start > 0 and len(sent[start - 1].split()) <= 8:
        start -= 1
    quote = " ".join(sent[start : end + 1])
    return quote if quote in segment["text"] else sent[scored[0]]


def top_pairs(transcript: dict, topic: str, k: int = 2) -> list[dict]:
    """The (question, answer) turn pairs that address a topic, best first.

    Returns up to two, because the guide bundles some questions (training *and* outcomes) and
    experts split their answer across a follow-up exchange.

    The gate matters. The first pair qualifies if the interviewer asked about the topic OR the
    answer holds at least two evidence terms. Any additional pair must have been asked about
    directly: without that, a passing mention of "capital budget" in the adoption answer got
    pulled in as a second barriers quote, because nearly every turn here mentions money. That
    extra pair must also be *exclusively* about the topic, since the barriers question asks what
    is holding adoption back and would otherwise supply a second adoption quote.
    """
    scored = []
    for p in pairs(transcript):
        if p["answer"] is None:
            continue
        qh = _question_hits(p["question"]["text"], topic)
        th = _term_hits(p["answer"]["text"], topic)
        if qh == 0 and th < 2:
            continue
        scored.append((2 * qh + th, qh, p))
    scored.sort(key=lambda t: (-t[0], t[2]["answer"]["start_s"]))

    direct = [(qh, p) for _, qh, p in scored if qh > 0]
    if not direct:
        return [p for _, _, p in scored][:1]
    kept = [direct[0][1]]
    for _, p in direct[1:]:
        if len(kept) == k:
            break
        if _asked_about(p["question"]["text"], topic):
            kept.append(p)
    # Chronological: the guide question is answered first, the follow-up second. Score order put the
    # later follow-up first when its question matched more cues, which read as if the guide question
    # had been answered with a different question's turn.
    kept.sort(key=lambda p: p["answer"]["start_s"])
    return kept


def best_pair(transcript: dict, topic: str) -> dict | None:
    """The single best (question, answer) pair for a topic, or None if the call skipped it."""
    got = top_pairs(transcript, topic, k=1)
    return got[0] if got else None


def _quote_obj(seg: dict, topic: str) -> dict:
    return {
        "text": best_quote(seg, topic),
        "timestamp": seg["timestamp"],
        "speaker": seg["speaker"],
        "segment_id": seg["id"],
        "expert": seg["market"],
        "topic": topic,
    }


def guide_answers(transcripts: list[dict], guide: list[dict]) -> list[dict]:
    """One answer per expert per question, each carrying verbatim quotes with timestamps.

    Up to two supporting turns per expert: the guide bundles training with outcomes, and some
    experts split that answer across a follow-up exchange, so one quote would lose half of it.
    """
    out = []
    for q in guide:
        answers = []
        for t in transcripts:
            found = top_pairs(t, q["topic"], k=2)
            quotes = [_quote_obj(p["answer"], q["topic"]) for p in found]
            answers.append(
                {
                    "expert": t["market"],
                    "expert_name": t["expert"],
                    "role": t["role"],
                    "not_covered": not found,
                    "interviewer_question": found[0]["question"]["text"] if found else None,
                    "question_timestamp": found[0]["question"]["timestamp"] if found else None,
                    "confidence": (
                        min(1.0, round(_question_hits(found[0]["question"]["text"], q["topic"]) / 1.5, 2))
                        if found
                        else 0.0
                    ),
                    "quotes": quotes,
                }
            )
        out.append({**q, "answers": answers})
    return out


# --- themes and disagreements ------------------------------------------------------------------

# A disagreement is reported only on a signal that can be read back out of the transcripts:
#   1. the experts quantify the same thing differently ("15 to 20 percent" vs "high single digits")
#   2. one expert redirects to a different driver than the others (asked about barriers, answers
#      about training capacity)
#   3. one expert explicitly rejects the others' claim ("I would not say finance alone decides")
# A generic "hedges where others assert" test was tried first and misfired: the UK expert's
# "training capacity is just as important" sentence is the disagreement on barriers and simple
# agreement on training, and only the redirect test can tell those two apart.
REJECTION_CUES = ["would not say", "does not decide", "not purely", "not always", "rather than",
                 "not necessarily", "than finance alone"]
PRIMACY_CUES = ["very important", "biggest", "the biggest", "first barrier", "the first", "is the first",
                "decides", "main ", "key point"]

# Longest first, else "eight" matches before "eighteen" and "nine to eighteen" reads as "Nine to eight".
_NUM_WORDS = sorted(
    ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
     "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
     "thirty", "forty", "fifty"],
    key=len,
    reverse=True,
)
_NUM = rf"(?:\d+|(?:{'|'.join(_NUM_WORDS)})(?:[ -](?:{'|'.join(_NUM_WORDS)}))?)"
RANGE_RE = re.compile(rf"\b({_NUM})\s*(?:to|-)\s*({_NUM})\s*(percent|%|months?|weeks?|years?)?", re.I)
DIGITS_RE = re.compile(
    r"\b(?:high |low |mid )?(?:single|double) digits(?:\s+or\s+(?:high |low )?(?:single|double) digits)?", re.I
)


def _quantifier(text: str) -> str | None:
    """A short verbatim span naming how much / how long, e.g. '15 to 20 percent'."""
    if m := DIGITS_RE.search(text):
        return m.group(0)
    if m := RANGE_RE.search(text):
        return m.group(0).strip()
    return None


def _rejects(text: str) -> bool:
    low = text.lower()
    return any(c in low for c in REJECTION_CUES)


def _asserts(text: str) -> bool:
    low = text.lower()
    return any(c in low for c in PRIMACY_CUES)


def _redirects(text: str, topic: str) -> bool:
    """True when a turn argues a different topic harder than the one being discussed."""
    own = _term_hits(text, topic)
    other = max((_term_hits(text, t) for t, _ in TOPICS if t != topic), default=0)
    return other > own


def _view(transcript: dict, topic: str) -> dict | None:
    pair = best_pair(transcript, topic)
    if not pair:
        return None
    answer = pair["answer"]
    return {
        "expert": answer["market"],
        "speaker": answer["speaker"],
        "timestamp": answer["timestamp"],
        "segment_id": answer["id"],
        "quote": best_quote(answer, topic),
        "quantifier": _quantifier(answer["text"]),
        "redirects": _redirects(answer["text"], topic),
        "rejects": _rejects(answer["text"]),
        "asserts": _asserts(answer["text"]),
    }


def themes_and_disagreements(transcripts: list[dict], guide: list[dict]) -> dict:
    """Per topic: a theme when >=2 experts have a view, a disagreement when their views conflict."""
    themes, disagreements = [], []

    for q in guide:
        topic = q["topic"]
        views = [v for t in transcripts if (v := _view(t, topic))]
        if len(views) < 2:
            continue

        themes.append(
            {
                "topic": topic,
                "name": q["name"],
                "question": q["question"],
                "expert_count": len(views),
                "total_experts": len(transcripts),
                "experts": [v["expert"] for v in views],
                "views": views,
            }
        )

        quantifiers = {v["expert"]: v["quantifier"] for v in views if v["quantifier"]}
        quant_diverges = len(set(quantifiers.values())) > 1
        redirection = [v for v in views if v["redirects"]]
        rejection = [v for v in views if v["rejects"]] if any(v["asserts"] for v in views) else []

        if quant_diverges:
            reason = "experts quantify this differently"
        elif rejection:
            reason = "one expert explicitly qualifies what the others state as fact"
        elif redirection:
            reason = "one expert names a different primary driver than the others"
        else:
            continue

        disagreements.append(
            {
                "topic": topic,
                "name": q["name"],
                "question": q["question"],
                "reason": reason,
                "sides": views,
            }
        )

    return {"themes": themes, "disagreements": disagreements}


# --- Q&A retrieval ----------------------------------------------------------------------------

STOP = {"the", "and", "for", "are", "was", "were", "does", "did", "how", "what", "when", "why",
        "who", "which", "that", "this", "with", "you", "your", "they", "them", "their", "have",
        "has", "had", "about", "into", "from", "over", "under", "can", "could", "would", "should",
        "there", "then", "than", "its", "not", "but", "all", "any", "our", "out", "get", "many",
        "much", "some", "more", "most", "long", "take", "typical", "usually", "important", "main",
        "current", "next", "years", "year", "say", "said", "tell", "according", "experts", "expert"}
SYNONYMS = {"buy": "purchas", "buys": "purchas", "buying": "purchas", "purchase": "purchas",
            "purchasing": "purchas", "purchases": "purchas", "cost": "price", "costs": "price",
            "robot": "robotic", "robots": "robotic", "barriers": "barrier", "timeline": "month",
            "growth": "grow", "training": "train", "decision": "decid", "decisions": "decid",
            "months": "month", "often": "month"}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z]{3,}", text.lower())
    return {SYNONYMS.get(w, w) for w in words if w not in STOP}


def _overlap(a: str, b: str) -> bool:
    """Cheap stem match on the first four characters: purchas/purchasing, month/months."""
    return a == b or (len(a) >= 4 and len(b) >= 4 and a[:4] == b[:4])


def match_topic(question: str) -> str | None:
    """Route a free-form question to a guide topic. None = fall back to plain search.

    Longest cue wins, so "the main barrier to adoption" routes to barriers rather than adoption,
    which a first-match-wins loop got wrong because "adoption" is a shorter cue.
    """
    low = question.lower()
    best: tuple[int, str] | None = None
    for topic, cues in TOPIC_CUES.items():
        for cue in cues:
            if cue in low and (best is None or len(cue) > best[0]):
                best = (len(cue), topic)
    return best[1] if best else None


def lexical_search(question: str, segments: list[dict], k: int = 4) -> list[dict]:
    """Top-k expert turns by shared vocabulary. No key, no network, still fully citable.

    A single shared word is not evidence. "What is the capital of Peru?" matched "capital budgets"
    in half the corpus and came back as a confident, cited, wrong answer. Requiring two matching
    content terms (or the only one the question has) is what makes the no-evidence path reachable.
    """
    q = _tokens(question)
    if not q:
        return []
    need = min(len(q), 2)
    scored = []
    for seg in segments:
        if not seg["is_expert"]:
            continue
        words = _tokens(seg["text"])
        hits = sum(1 for w in q if any(_overlap(w, x) for x in words))
        if hits >= need:
            scored.append((hits, seg))
    scored.sort(key=lambda t: (-t[0], t[1]["start_s"], t[1]["market"]))
    return [s for _, s in scored[:k]]


def retrieve(question: str, transcripts: list[dict], k: int = 4) -> tuple[list[dict], str | None]:
    """Evidence for a question. Topic-routed through the turn pairs when it matches the guide.

    Topic routing exists because a bare keyword search put "How long does purchasing take?" on the
    barrier turns: every turn in these calls contains the word "purchasing".
    """
    topic = match_topic(question)
    if topic:
        hits = [p["answer"] for t in transcripts for p in top_pairs(t, topic, k=2)]
        if hits:
            hits.sort(key=lambda s: s["start_s"])
            return hits[:k], topic
    return lexical_search(question, [s for t in transcripts for s in t["segments"]], k=k), None


def evidence_pack(segments: list[dict]) -> str:
    """The only thing an LLM is ever allowed to see."""
    return "\n".join(f"[{s['timestamp']}, {s['speaker']}, {s['market']}] {s['text']}" for s in segments)


def golden() -> dict:
    return json.loads((DATA / "golden_dataset.json").read_text(encoding="utf-8"))