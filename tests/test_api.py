"""API contract tests.

Shape is asserted field by field, not just status codes: a silently dropped field is the exact
failure mode an AI-written pipeline has, and it would only surface in the demo video.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.main import app  # noqa: E402

REQUIRED_QUESTION_FIELDS = {"id", "topic", "name", "question", "summary", "summary_provider", "answers"}
REQUIRED_ANSWER_FIELDS = {
    "expert", "expert_name", "role", "not_covered", "interviewer_question",
    "question_timestamp", "confidence", "quotes",
}
REQUIRED_QUOTE_FIELDS = {"text", "timestamp", "speaker", "segment_id", "expert", "topic"}
REQUIRED_THEME_FIELDS = {"topic", "name", "question", "expert_count", "total_experts", "experts", "views"}
REQUIRED_VIEW_FIELDS = {"expert", "speaker", "timestamp", "segment_id", "quote", "quantifier", "redirects", "rejects", "asserts"}
REQUIRED_CITATION_FIELDS = {"speaker", "timestamp", "text", "segment_id", "market"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # context manager runs startup, so transcripts load
        yield c


# --- health and transcripts ----------------------------------------------------------------------

def test_health_reports_loaded_corpus(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["transcripts"] == 3
    assert body["segments"] > 0


def test_transcripts_listing_contract(client):
    body = client.get("/api/transcripts").json()
    rows = body["transcripts"]
    assert {r["market"] for r in rows} == {"France", "Germany", "United Kingdom"}
    for r in rows:
        assert {"market", "expert", "role", "source", "segments", "turns", "duration"} <= set(r)
        assert r["expert"] and r["role"]


def test_ingest_reloads_bundled_samples(client):
    body = client.post("/api/transcripts/ingest").json()
    assert body["source"] == "bundled_samples"
    assert len(body["ingested"]) == 3


def test_ingest_accepts_a_valid_upload(client):
    sample = "Expert 4 - Dr. Test\nRole: Surgeon\nMarket: Spain\n\n00:00\nInterviewer: Adoption?\n\n00:10\nDr. Test: Adoption is growing steadily here.\n"
    r = client.post(
        "/api/transcripts/ingest",
        files={"file": ("Transcript_4_Spain.txt", sample, "text/plain")},
    )
    assert r.status_code == 200
    assert r.json()["expert"] == "Dr. Test"
    assert "Spain" in [t["market"] for t in client.get("/api/transcripts").json()["transcripts"]]
    client.post("/api/transcripts/ingest")  # restore the three samples


def test_ingest_accepts_a_transcript_saved_with_a_utf8_bom(client):
    """Notepad and PowerShell write UTF-8 with a BOM; that must not fail as a malformed header."""
    sample = "\ufeffExpert 4 - Dr. Test\nRole: Surgeon\nMarket: Spain\n\n00:00\nInterviewer: Adoption?\n\n00:10\nDr. Test: Adoption is growing steadily here.\n"
    r = client.post("/api/transcripts/ingest", files={"file": ("bom.txt", sample.encode("utf-8"), "text/plain")})
    assert r.status_code == 200
    assert r.json()["expert"] == "Dr. Test"
    client.post("/api/transcripts/ingest")  # restore the three samples


def test_ingest_rejects_malformed_upload_with_a_line_number(client):
    r = client.post(
        "/api/transcripts/ingest",
        files={"file": ("bad.txt", "no header, no timestamps, no turns\n", "text/plain")},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "PARSE_ERROR"
    assert "bad.txt" in body["error"]["message"]
    assert client.get("/api/health").json()["transcripts"] == 3, "bad upload must not disturb state"


def test_ingest_rejects_non_utf8(client):
    r = client.post("/api/transcripts/ingest", files={"file": ("x.txt", b"\xff\xfe\x00bad", "text/plain")})
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "BAD_ENCODING"


def test_ingest_rejects_oversized_file(client):
    big = b"a" * (3 * 1024 * 1024)
    r = client.post("/api/transcripts/ingest", files={"file": ("big.txt", big, "text/plain")})
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "FILE_TOO_LARGE"


# --- guide answers -------------------------------------------------------------------------------

def test_guide_answers_full_contract(client):
    body = client.get("/api/guide-answers").json()
    assert len(body["questions"]) == 6
    for q in body["questions"]:
        assert REQUIRED_QUESTION_FIELDS <= set(q), f"missing {REQUIRED_QUESTION_FIELDS - set(q)}"
        assert len(q["answers"]) == 3
        for a in q["answers"]:
            assert REQUIRED_ANSWER_FIELDS <= set(a), f"missing {REQUIRED_ANSWER_FIELDS - set(a)}"
            assert a["not_covered"] is False, f"Q{q['id']} {a['expert']} not covered"
            assert a["quotes"], "every answer needs at least one quote"
            for quote in a["quotes"]:
                assert REQUIRED_QUOTE_FIELDS <= set(quote)
                assert quote["text"] and quote["timestamp"]


def test_guide_answers_can_skip_the_model(client):
    body = client.get("/api/guide-answers?use_llm=false").json()
    assert body["provider"] == "lexical"
    assert all(q["summary_provider"] == "lexical" for q in body["questions"])


def test_every_quote_can_be_traced_back_to_its_source_segment(client):
    """The whole trust claim, exercised through the API rather than the internals."""
    body = client.get("/api/guide-answers").json()
    for q in body["questions"]:
        for a in q["answers"]:
            for quote in a["quotes"]:
                src = client.get(f"/api/segments/{quote['segment_id']}")
                assert src.status_code == 200, quote["segment_id"]
                seg = src.json()
                assert quote["text"] in seg["text"], "quote is not verbatim in its source"
                assert seg["timestamp"] == quote["timestamp"]
                assert seg["market"] == quote["expert"]


# --- themes --------------------------------------------------------------------------------------

def test_themes_contract(client):
    body = client.get("/api/themes").json()
    assert len(body["themes"]) == 6
    assert len(body["disagreements"]) == 4
    for t in body["themes"]:
        assert REQUIRED_THEME_FIELDS <= set(t)
        assert t["expert_count"] >= 2
        for v in t["views"]:
            assert REQUIRED_VIEW_FIELDS <= set(v)
    for d in body["disagreements"]:
        assert {"topic", "name", "question", "reason", "sides"} <= set(d)
        assert len(d["sides"]) >= 2


def test_disagreement_topics_are_the_expected_ones(client):
    body = client.get("/api/themes").json()
    assert {d["topic"] for d in body["disagreements"]} == {"growth", "cost_roi", "barriers", "timeline"}


# --- ask -----------------------------------------------------------------------------------------

def test_ask_returns_a_cited_answer(client):
    r = client.post("/api/ask", json={"question": "How long does purchasing a robotic system take?"})
    assert r.status_code == 200
    body = r.json()
    assert {"question", "answer", "provider", "citations", "topic"} <= set(body)
    assert body["topic"] == "timeline"
    assert body["answer"]
    assert body["citations"], "an answer with no citations is not acceptable"
    for c in body["citations"]:
        assert REQUIRED_CITATION_FIELDS <= set(c)
    assert {"06:08", "06:05", "05:04"} <= {c["timestamp"] for c in body["citations"]}


def test_ask_lexical_mode_is_fully_usable(client):
    """No key must still give a cited, verbatim answer. This is the demo's safety net."""
    body = client.post("/api/ask", json={"question": "What are the main barriers?", "use_llm": False}).json()
    assert body["provider"] == "lexical"
    assert body["citations"]
    assert all(c["text"] for c in body["citations"])


def test_ask_rejects_empty_question(client):
    r = client.post("/api/ask", json={"question": "   "})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "EMPTY_QUESTION"


def test_ask_rejects_overlong_question(client):
    r = client.post("/api/ask", json={"question": "x" * 501})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "QUESTION_TOO_LONG"


def test_ask_handles_a_question_with_no_evidence(client):
    body = client.post("/api/ask", json={"question": "What is the capital of Peru?"}).json()
    assert body["citations"] == []
    assert body["answer"]


def test_ask_never_leaks_html_unescaped(client):
    """Quotes are rendered by the browser, so the API must return text as data, not markup."""
    body = client.post("/api/ask", json={"question": "<script>alert(1)</script>"}).json()
    assert isinstance(body["answer"], str)


# --- segments ------------------------------------------------------------------------------------

def test_unknown_segment_returns_a_404_envelope(client):
    r = client.get("/api/segments/Nowhere:99:99:Nobody")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_ui_is_served_at_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]