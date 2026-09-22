"""The only place a model is called.

Design rule this file exists to enforce: the LLM is given evidence that app/analyze.py already
retrieved and verified, and it is only allowed to write prose over it. It never extracts quotes,
never invents timestamps, and its output is rejected if it cites a timestamp it was not given.

Provider is any OpenAI-compatible chat endpoint (default: Google Gemini's free tier). One httpx
POST covers it, so no provider SDK is needed.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _load_env_file(path: Path = ENV_FILE) -> None:
    """Read .env so plain `uvicorn app.main:app` picks up the key, without the --env-file flag.

    Stdlib only, deliberately not python-dotenv. A real environment variable always wins, so shell
    overrides and CI runs behave normally; a missing or empty file simply means verbatim mode.
    """
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        os.environ.setdefault(key, value.strip().strip("\"'"))


_load_env_file()

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
DEFAULT_MODEL = "gemini-2.0-flash"
TIMEOUT_S = float(os.getenv("LLM_TIMEOUT_S", "30"))

# ponytail: in-process dict cache, move to redis only if this ever runs multi-worker
_summary_cache: dict[str, dict] = {}

SYSTEM_QA = (
    "You answer questions about expert-call transcripts. "
    "Use ONLY the evidence lines provided. Do not add outside knowledge. "
    "Do not speculate. "
    "After every claim, cite the source as [MM:SS, Speaker]. "
    "Only cite timestamps that appear in the evidence. "
    "If the evidence does not answer the question, say exactly that. "
    "Be concise: at most 4 sentences. Plain prose, no markdown headings, no bullet lists."
)

SYSTEM_SUMMARY = (
    "You summarise what interview experts said, for an analyst. "
    "Use ONLY the quotes provided, which are already verbatim extracts. "
    "Do not add outside knowledge and do not invent numbers. "
    "Cover every expert you are given. Where experts differ, say so plainly. "
    "Cite each expert's point as [MM:SS, Expert]. "
    "Three sentences maximum. Plain prose, no markdown headings, no bullet lists."
)


def config() -> dict:
    return {
        "key": os.getenv("LLM_API_KEY", "").strip(),
        "base_url": os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/"),
        "model": os.getenv("LLM_MODEL", DEFAULT_MODEL).strip(),
        "mock": os.getenv("MOCK_LLM", "0").strip() in {"1", "true", "yes"},
    }


def available() -> bool:
    """True when we have a key, or when mock mode is on."""
    cfg = config()
    return bool(cfg["mock"] or cfg["key"])


def provider_name() -> str:
    cfg = config()
    if cfg["mock"]:
        return "mock"
    return cfg["model"] if cfg["key"] else "lexical"


# --- transport --------------------------------------------------------------------------------

class LLMError(RuntimeError):
    """Raised when the model could not be reached. Callers fall back to verbatim evidence."""


def _post(messages: list[dict], temperature: float = 0.2, attempts: int = 2) -> str:
    """One chat completion. Retries only transient failures, never a 4xx that will repeat."""
    cfg = config()
    if cfg["mock"]:
        return _mock_reply(messages)
    if not cfg["key"]:
        raise LLMError("no API key configured")

    last: Exception | None = None
    for attempt in range(attempts):
        try:
            r = httpx.post(
                f"{cfg['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {cfg['key']}", "Content-Type": "application/json"},
                json={"model": cfg["model"], "messages": messages, "temperature": temperature},
                timeout=TIMEOUT_S,
            )
            if r.status_code in (429, 500, 502, 503, 504):  # transient: retry
                last = LLMError(f"provider returned {r.status_code}")
                time.sleep(1.5 * (attempt + 1))
                continue
            if r.status_code >= 400:  # permanent: do not retry
                raise LLMError(f"provider returned {r.status_code}: {r.text[:200]}")
            return r.json()["choices"][0]["message"]["content"].strip()
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise LLMError(f"LLM unreachable after {attempts} attempts: {last}")


def _mock_reply(messages: list[dict]) -> str:
    """Offline stand-in used by tests and by demoing the pipeline without a key.

    Handles both evidence formats: segments carry "[ts, speaker, market]" and summary quote lines
    carry "[ts, expert]".
    """
    user = messages[-1]["content"]
    stamps = re.findall(r"\[(\d{2}:\d{2}), ([^,\]]+)(?:, ([^\]]+))?\]", user)
    if not stamps:
        return "The provided evidence does not answer that question."
    return " ".join(
        f"{who.strip()} at [{ts}, {what.strip()}] addresses this."
        for ts, what, who in ((ts, spk, mkt or spk) for ts, spk, mkt in stamps[:4])
    )


# --- citation guard ---------------------------------------------------------------------------

CITE_RE = re.compile(r"\[(\d{2}:\d{2})[,\]]")


def citations_ok(answer: str, evidence: list[dict]) -> tuple[bool, list[str]]:
    """Every timestamp the model cited must exist in the evidence it was handed.

    This is the check that turns 'we reduce hallucinations' from a claim into a test: a fabricated
    timestamp is caught here rather than shown to the user.
    """
    allowed = {s["timestamp"] for s in evidence}
    cited = set(CITE_RE.findall(answer))
    if not cited:
        return False, []
    return cited <= allowed, sorted(cited - allowed)


# --- public operations --------------------------------------------------------------------------

def answer_question(question: str, evidence: list[dict]) -> dict:
    """Grounded answer for a free-form question. Always returns citations; prose only if allowed."""
    from app.analyze import evidence_pack  # local import: analyze has no dependency on llm

    if not evidence:
        return verbatim_answer([], sufficient=False)
    if not available():
        return verbatim_answer(evidence)

    lexical = verbatim_answer(evidence)
    pack = evidence_pack(evidence)
    try:
        raw = _post(
            [
                {"role": "system", "content": SYSTEM_QA},
                {"role": "user", "content": f"Evidence:\n{pack}\n\nQuestion: {question}"},
            ]
        )
    except LLMError as e:
        log.warning("LLM unavailable, using verbatim evidence: %s", e)
        return {**lexical, "provider": "lexical", "note": f"model unavailable: {e}"}

    ok, bad = citations_ok(raw, evidence)
    if not ok:
        # One retry with the offending timestamps named, then fall back. Never show an unverified
        # citation.
        try:
            retry = _post(
                [
                    {"role": "system", "content": SYSTEM_QA},
                    {"role": "user", "content": f"Evidence:\n{pack}\n\nQuestion: {question}"},
                    {
                        "role": "assistant",
                        "content": raw,
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Your answer cited timestamps that are not in the evidence: {bad}. "
                            "Rewrite it citing only timestamps from the evidence."
                        ),
                    },
                ],
                temperature=0.0,
                attempts=1,
            )
            if citations_ok(retry, evidence)[0]:
                raw = retry
                ok = True
        except LLMError:
            pass

    if not ok:
        log.warning("citation check failed, falling back to verbatim evidence")
        return {**lexical, "provider": "lexical", "note": "model cited sources not present in the evidence"}

    return {"answer": raw, "provider": provider_name(), "citations": _citations(evidence)}


def summarize_question(question: dict, answers: list[dict]) -> dict:
    """Cross-expert prose summary of one guide question, over the quotes already extracted.

    Returns {"summary", "provider", "citations"} in every path. An earlier version let the lexical
    fallback return the answer-shaped dict, which silently broke the UI's no-key mode.
    """
    evidence = [q for a in answers for q in a["quotes"]]
    if not evidence:
        return {"summary": "", "provider": "lexical", "citations": []}
    if not available() or not _has_usable_evidence(evidence):
        return _lexical_summary(evidence)

    key = str(question["id"])
    if key in _summary_cache:
        return _summary_cache[key]

    lines = "\n".join(f"[{q['timestamp']}, {q['speaker']}] {q['text']}" for q in evidence)
    try:
        raw = _post(
            [
                {"role": "system", "content": SYSTEM_SUMMARY},
                {"role": "user", "content": f"Question: {question['question']}\n\nQuotes:\n{lines}"},
            ]
        )
    except LLMError as e:
        log.warning("LLM unavailable, using verbatim quotes: %s", e)
        return {**_lexical_summary(evidence), "note": f"model unavailable: {e}"}

    ok, bad = citations_ok(raw, evidence)
    if not ok:
        return {**_lexical_summary(evidence), "note": "model cited sources not present in the evidence"}

    out = {"summary": raw, "provider": provider_name(), "citations": _citations(evidence)}
    _summary_cache[key] = out
    return out


def _has_usable_evidence(evidence: list[dict]) -> bool:
    return all(e.get("timestamp") and e.get("text") for e in evidence)


def _lexical_summary(evidence: list[dict]) -> dict:
    """Deterministic summary: the experts' own words, grouped by expert, still cited."""
    return {
        "summary": " ".join(f"[{q['timestamp']}, {q['speaker']}] {q['text']}" for q in evidence),
        "provider": "lexical",
        "citations": _citations(evidence),
    }


def _citations(evidence: list[dict]) -> list[dict]:
    """Normalise both evidence shapes to one citation record.

    Two shapes reach this function: transcript segments (key "id") from retrieval, and quote
    objects (key "segment_id") from guide answers. Collapsing them here keeps every caller's
    output identical.
    """
    return [
        {
            "speaker": s["speaker"],
            "timestamp": s["timestamp"],
            "text": s["text"],
            "segment_id": s.get("segment_id") or s.get("id", ""),
            "market": s.get("market") or s.get("expert", ""),
        }
        for s in evidence
    ]


def verbatim_answer(evidence: list[dict], sufficient: bool = True) -> dict:
    """No model: read the evidence back verbatim, still fully cited.

    This is the default path with no key, and the fallback whenever the model is unavailable or
    cites something it was not given. It cannot be wrong, because it contains no generated text.

    When nothing relevant was found it says so plainly instead of returning an empty box, and when
    the evidence is only a weak match it labels it as such rather than passing it off as an answer.
    """
    if not evidence:
        return {
            "answer": "The transcripts do not contain evidence for that question.",
            "provider": "lexical",
            "citations": [],
            "sufficient": False,
        }
    if not sufficient:
        return {
            "answer": "No passage in the transcripts directly addresses that question. The closest related turns are shown below.",
            "provider": "lexical",
            "citations": _citations(evidence),
            "sufficient": False,
        }
    return {
        "answer": " ".join(f"[{s['timestamp']}, {s['speaker']}] {s['text']}" for s in evidence),
        "provider": "lexical",
        "citations": _citations(evidence),
        "sufficient": True,
    }


def reset_cache() -> None:
    _summary_cache.clear()


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(available(), indent=None))
    print("provider:", provider_name())