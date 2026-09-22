"""Tests for the LLM layer. No network and no key: every case runs through MOCK_LLM or a stub.

The citation guard is the point of this file. 'We reduce hallucinations' is only a real claim if a
fabricated timestamp is provably rejected, so that is what these tests pin down.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import analyze as A  # noqa: E402
from app import llm  # noqa: E402

TRANSCRIPTS = A.load_transcripts()


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """Default every test to offline mode with a blank key, so nothing reaches the network."""
    monkeypatch.setenv("MOCK_LLM", "1")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    llm.reset_cache()
    yield


@pytest.fixture
def evidence():
    segs, _ = A.retrieve("How long does purchasing a robotic system take?", TRANSCRIPTS)
    return segs


# --- config -------------------------------------------------------------------------------------

def test_reports_unavailable_without_key_or_mock(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "0")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert llm.available() is False
    assert llm.provider_name() == "lexical"


def test_reports_available_in_mock_mode():
    assert llm.available() is True
    assert llm.provider_name() == "mock"


def test_provider_name_reports_configured_model(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "0")
    monkeypatch.setenv("LLM_API_KEY", "test-key-not-real")
    monkeypatch.setenv("LLM_MODEL", "gemini-2.0-flash")
    assert llm.provider_name() == "gemini-2.0-flash"


# --- citation guard -----------------------------------------------------------------------------

def test_citation_guard_accepts_only_evidence_timestamps(evidence):
    allowed = evidence[0]["timestamp"]
    ok, bad = llm.citations_ok(f"Something happened [{allowed}, X].", evidence)
    assert ok is True
    assert bad == []


def test_citation_guard_rejects_invented_timestamp(evidence):
    ok, bad = llm.citations_ok("Something happened [99:99, Dr. Nobody].", evidence)
    assert ok is False
    assert bad == ["99:99"]


def test_citation_guard_rejects_answer_with_no_citations(evidence):
    ok, bad = llm.citations_ok("A confident sentence with no source at all.", evidence)
    assert ok is False
    assert bad == []


def test_citation_guard_flags_only_the_fabricated_one(evidence):
    good = evidence[0]["timestamp"]
    ok, bad = llm.citations_ok(f"True [{good}, A] and false [12:34, B].", evidence)
    assert ok is False
    assert bad == ["12:34"]


# --- grounded answering -------------------------------------------------------------------------

def test_answer_is_cited_and_grounded(evidence):
    out = llm.answer_question("How long does purchasing take?", evidence)
    assert out["answer"]
    assert out["provider"] == "mock"
    assert {c["timestamp"] for c in out["citations"]} == {s["timestamp"] for s in evidence}
    for c in out["citations"]:
        assert c["speaker"] and c["segment_id"] and c["market"]


def test_answer_without_key_falls_back_to_verbatim_evidence(monkeypatch, evidence):
    monkeypatch.setenv("MOCK_LLM", "0")
    out = llm.answer_question("How long does purchasing take?", evidence)
    assert out["provider"] == "lexical"
    # verbatim fallback: the real transcript text is shown, and it is cited
    assert evidence[0]["text"] in out["answer"]
    assert len(out["citations"]) == len(evidence)


def test_answer_says_so_when_there_is_no_evidence():
    out = llm.answer_question("What is the capital of Peru?", [])
    assert out["citations"] == []
    assert "do not contain evidence" in out["answer"]


def test_answer_never_calls_the_model_when_no_key_and_no_mock(monkeypatch, evidence):
    monkeypatch.setenv("MOCK_LLM", "0")
    called = {"n": 0}

    def boom(*a, **k):
        called["n"] += 1
        raise AssertionError("network must not be touched in lexical mode")

    monkeypatch.setattr(llm.httpx, "post", boom)
    out = llm.answer_question("timeline?", evidence)
    assert out["provider"] == "lexical"
    assert called["n"] == 0


def test_hallucinated_citation_triggers_fallback(monkeypatch, evidence):
    """A model that invents a timestamp must not be shown to the user."""
    monkeypatch.setenv("MOCK_LLM", "0")
    monkeypatch.setenv("LLM_API_KEY", "test-key-not-real")

    replies = iter(["Invented claim [99:99, Nobody].", "Still invented [98:98, Nobody]."])
    monkeypatch.setattr(llm, "_post", lambda *a, **k: next(replies))

    out = llm.answer_question("How long does purchasing take?", evidence)
    assert out["provider"] == "lexical"
    assert "not present in the evidence" in out.get("note", "")
    assert evidence[0]["text"] in out["answer"]


def test_retry_after_bad_citation_is_accepted_when_corrected(monkeypatch, evidence):
    monkeypatch.setenv("MOCK_LLM", "0")
    monkeypatch.setenv("LLM_API_KEY", "test-key-not-real")
    good = evidence[0]["timestamp"]

    replies = iter(["Bad [99:99, Nobody].", f"Corrected [{good}, {evidence[0]['speaker']}]."])
    monkeypatch.setattr(llm, "_post", lambda *a, **k: next(replies))

    out = llm.answer_question("How long does purchasing take?", evidence)
    assert out["provider"] != "lexical"
    assert "Corrected" in out["answer"]


def test_llm_error_falls_back_rather_than_failing(monkeypatch, evidence):
    monkeypatch.setenv("MOCK_LLM", "0")
    monkeypatch.setenv("LLM_API_KEY", "test-key-not-real")

    def dead(*a, **k):
        raise llm.LLMError("provider returned 503")

    monkeypatch.setattr(llm, "_post", dead)
    out = llm.answer_question("timeline?", evidence)
    assert out["provider"] == "lexical"
    assert evidence[0]["text"] in out["answer"]


# --- summaries ------------------------------------------------------------------------------------

def test_summary_uses_extracted_quotes_and_is_cached(evidence):
    guide = A.load_guide()
    answers = A.guide_answers(TRANSCRIPTS, guide)[0]["answers"]
    first = llm.summarize_question(guide[0], answers)
    assert first["summary"]
    assert first["provider"] == "mock"
    assert llm._summary_cache, "summary should be cached after first call"
    assert llm.summarize_question(guide[0], answers) == first


def test_summary_with_no_quotes_returns_empty_not_an_error():
    out = llm.summarize_question({"id": 99, "question": "?"}, [])
    assert out["summary"] == ""
    assert out["citations"] == []


def test_mock_reply_handles_no_evidence_lines():
    assert "does not answer" in llm._mock_reply([{"role": "user", "content": "nothing here"}])