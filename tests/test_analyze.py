"""Golden-dataset tests for the deterministic core.

Every expected value here was read by hand off the transcripts and lives in
data/golden_dataset.json. If extraction drifts, these fail loudly instead of the demo quietly
showing a wrong quote.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import analyze as A  # noqa: E402

GOLD = A.golden()
TRANSCRIPTS = A.load_transcripts()
GUIDE = A.load_guide()


@pytest.fixture(scope="module")
def all_segments():
    return [s for t in TRANSCRIPTS for s in t["segments"]]


# --- parsing ----------------------------------------------------------------------------------

def test_parses_all_three_transcripts():
    assert [t["market"] for t in TRANSCRIPTS] == ["France", "Germany", "United Kingdom"]


@pytest.mark.parametrize("market", ["France", "Germany", "United Kingdom"])
def test_expert_header_and_turn_counts(market):
    t = next(x for x in TRANSCRIPTS if x["market"] == market)
    assert t["expert"], f"{market}: expert name not parsed"
    assert t["role"], f"{market}: role not parsed"
    assert len(t["segments"]) == GOLD["segment_counts"][market]
    assert sum(s["is_expert"] for s in t["segments"]) == GOLD["expert_segment_counts"][market]


def test_every_turn_has_a_timestamp_and_text():
    for t in TRANSCRIPTS:
        for s in t["segments"]:
            assert s["timestamp"], s
            assert s["text"].strip()
            assert len(s["timestamp"]) == 5 and s["timestamp"][2] == ":"


def test_pairs_interviewer_question_with_expert_answer():
    for t in TRANSCRIPTS:
        prs = A.pairs(t)
        assert len(prs) == GOLD["expert_segment_counts"][t["market"]]
        for p in prs:
            assert p["answer"] is not None, f"{t['market']}: interviewer turn with no answer"


def test_rejects_malformed_transcript():
    with pytest.raises(ValueError):
        A.parse_transcript("00:10\nNobody speaks\n\nnot a transcript at all", "bad.txt")


def test_rejects_transcript_with_no_turns():
    with pytest.raises(ValueError):
        A.parse_transcript("Market: Nowhere\n", "empty.txt")


# --- guide loading ----------------------------------------------------------------------------

def test_guide_has_six_numbered_questions():
    assert [q["id"] for q in GUIDE] == [1, 2, 3, 4, 5, 6]
    assert all(q["question"].strip() for q in GUIDE)


# --- guide answers (18 golden expectations) ---------------------------------------------------

@pytest.fixture(scope="module")
def answers():
    return A.guide_answers(TRANSCRIPTS, GUIDE)


def test_all_eighteen_answers_present(answers):
    assert len(answers) == 6
    for q in answers:
        assert len(q["answers"]) == 3, f"Q{q['id']} should answer all three experts"


def test_answers_match_golden_timestamp_and_wording(answers):
    for q in answers:
        for a in q["answers"]:
            exp = GOLD["answers"][str(q["id"])][a["expert"]]
            assert not a["not_covered"], f"Q{q['id']} {a['expert']} unexpectedly not covered"
            joined = " ".join(x["text"] for x in a["quotes"])
            assert exp["contains"] in joined, (
                f"Q{q['id']} {a['expert']}: expected {exp['contains']!r} in quote, got {joined[:160]!r}"
            )
            assert exp["timestamp"] in [x["timestamp"] for x in a["quotes"]], (
                f"Q{q['id']} {a['expert']}: expected evidence at {exp['timestamp']}"
            )


def test_a_question_answer_is_not_labelled_with_another_topic(answers):
    """One quote per expert on current adoption: the barriers turn must not appear as adoption.

    The barriers question is literally "What is holding adoption back?", so the second-pair gate
    pulled the barriers answer into the adoption answer. Real quote, wrong label.
    """
    adoption = next(q for q in answers if q["topic"] == "adoption")
    for a in adoption["answers"]:
        expected = GOLD["answers"]["1"][a["expert"]]["timestamp"]
        assert [x["timestamp"] for x in a["quotes"]] == [expected], a

    # ...while an answer that legitimately spans two turns still carries both.
    training = next(q for q in answers if q["topic"] == "training_outcomes")
    france = next(a for a in training["answers"] if a["expert"] == "France")
    assert [x["timestamp"] for x in france["quotes"]] == ["03:10", "04:08"]


def test_every_quote_is_verbatim_and_carries_a_timestamp(answers):
    """The anti-hallucination contract: no quote may be a paraphrase."""
    for q in answers:
        for a in q["answers"]:
            for quote in a["quotes"]:
                source = next(
                    s for t in TRANSCRIPTS for s in t["segments"] if s["id"] == quote["segment_id"]
                )
                assert quote["text"] in source["text"], (
                    f"quote is not an exact substring of {quote['segment_id']}"
                )
                assert quote["timestamp"] == source["timestamp"]
                assert quote["speaker"] == source["speaker"]


def test_quote_segments_belong_to_the_expert_being_quoted(answers):
    for q in answers:
        for a in q["answers"]:
            for quote in a["quotes"]:
                assert quote["expert"] == a["expert"], (
                    f"{a['expert']}: quote taken from {quote['expert']}"
                )


# --- themes and disagreements -----------------------------------------------------------------

@pytest.fixture(scope="module")
def td():
    return A.themes_and_disagreements(TRANSCRIPTS, GUIDE)


def test_themes_cover_every_expected_topic(td):
    got = {t["topic"] for t in td["themes"]}
    assert got == {t["topic"] for t in GOLD["themes"]}, f"themes: {sorted(got)}"


def test_each_theme_spans_at_least_two_experts(td):
    for t in td["themes"]:
        assert t["expert_count"] >= 2, t
        assert len(t["views"]) == t["expert_count"]


def test_disagreements_match_golden_topics(td):
    got = {d["topic"] for d in td["disagreements"]}
    assert got == {d["topic"] for d in GOLD["disagreements"]}, f"disagreements: {sorted(got)}"


def test_golden_disagreement_sides_quote_the_right_experts(td):
    for exp in GOLD["disagreements"]:
        d = next(x for x in td["disagreements"] if x["topic"] == exp["topic"])
        for expert, marker in exp["sides"].items():
            side = next((s for s in d["sides"] if s["expert"] == expert), None)
            assert side is not None, f"{exp['topic']}: no view from {expert}"
            blob = side["quote"] + " " + (side["quantifier"] or "")
            assert marker in blob, f"{exp['topic']}/{expert}: expected {marker!r} in {blob[:160]!r}"


def test_theme_and_disagreement_quotes_are_verbatim(td):
    items = [*td["themes"], *td["disagreements"]]
    for item in items:
        for view in item.get("views", item.get("sides", [])):
            source = next(
                s for t in TRANSCRIPTS for s in t["segments"] if s["id"] == view["segment_id"]
            )
            assert view["quote"] in source["text"], view["segment_id"]


# --- Q&A retrieval ------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "question,topic",
    [
        ("How long does purchasing a robotic system take?", "timeline"),
        ("What is the main barrier to adoption?", "barriers"),
        ("How important is ROI?", "cost_roi"),
        ("Is growth going to be fast?", "growth"),
    ],
)
def test_question_routes_to_the_right_topic(question, topic):
    assert A.match_topic(question) == topic


@pytest.mark.parametrize(
    "question,expected_timestamps",
    [
        ("How long does purchasing a robotic system take?", {"06:08", "06:05", "05:04"}),
        ("What is the main barrier to adoption?", {"01:20", "01:10", "01:05"}),
    ],
)
def test_retrieval_finds_the_evidence_for_every_expert(question, expected_timestamps, all_segments):
    segs, _ = A.retrieve(question, TRANSCRIPTS)
    got = {s["timestamp"] for s in segs}
    assert expected_timestamps <= got, f"missing {expected_timestamps - got}"
    assert {s["market"] for s in segs if s["timestamp"] in expected_timestamps} == {
        "France",
        "Germany",
        "United Kingdom",
    }


def test_bare_keyword_question_falls_back_to_search(all_segments):
    segs, topic = A.retrieve("What did they say about maintenance contracts?", TRANSCRIPTS)
    assert topic is None
    assert segs, "lexical fallback returned nothing"
    assert any("maintenance" in s["text"].lower() for s in segs)


def test_retrieval_is_deterministic():
    q = "What are the main barriers?"
    a = [s["id"] for s in A.retrieve(q, TRANSCRIPTS)[0]]
    b = [s["id"] for s in A.retrieve(q, TRANSCRIPTS)[0]]
    assert a == b


def test_evidence_pack_carries_speaker_timestamp_and_market():
    segs, _ = A.retrieve("How long does purchasing take?", TRANSCRIPTS)
    pack = A.evidence_pack(segs)
    for s in segs:
        assert s["timestamp"] in pack and s["speaker"] in pack and s["market"] in pack