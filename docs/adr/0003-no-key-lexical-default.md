# ADR 0003 - No-key lexical mode is the default, the model is opt-in

**Status:** accepted (2026-09-22)

## Context

The evaluator's machine may have no API key and no network. If the app requires a key, the demo fails
for reasons that have nothing to do with the work being demonstrated. If the app requires a key and the
key is present, every failure mode of a remote API becomes a failure mode of the demo.

## Decision

Retrieval is lexical overlap over expert turns with a two-content-term minimum, and lexical mode answers
by returning the retrieved evidence verbatim, fully cited. The model layer (`app/llm.py`) is only
entered when `LLM_API_KEY` is set or `MOCK_LLM=1`; any timeout, provider error or failed citation check
falls back to the same verbatim path with a `note` explaining why. Every response carries a `provider`
field so the UI can show which path produced the answer.

## Consequences

- `pytest` and the demo both run offline with zero configuration; the model path is verified with
  `MOCK_LLM=1` and with stubbed replies, so no test needs network access.
- Lexical answers are less fluent than model prose. For this corpus that is the honest trade: the
  answer is the expert's own sentence with a timestamp, which is the format the brief asks for.
- Adding a second retrieval strategy later (embeddings) means adding a scorer beside
  `lexical_search`, not restructuring the pipeline.
