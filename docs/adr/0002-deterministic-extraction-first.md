# ADR 0002 - Deterministic extraction first, model last

**Status:** accepted (2026-09-22)

## Context

The brief's hard requirement is "do not invent information", and the demo requires exact quotes,
source timestamps for every answer, and traceable themes. Asking a model to extract quotes or
timestamps is the standard approach and the standard failure: it paraphrases, and it invents timestamps
it has no way to know.

## Decision

Everything structural is plain code in `app/analyze.py`:

- the parser turns `MM:SS` + `Speaker: text` into segments, so timestamps are data from the file;
- transcripts are strictly paired (interviewer turn, then that expert's answer), so a guide question
  routes to an answer by lookup instead of by keyword scoring. Keyword scoring was tried first and
  picked the wrong turn (an ROI answer for the training question);
- quotes are contiguous verbatim spans of a source turn, so `quote in segment_text` is checkable;
- themes need 2+ experts on a topic; disagreements need a quantified divergence, an explicit rejection
  or a redirect to a different driver.

A model may only write prose over evidence the code has already retrieved and verified, and its output
is discarded if it cites a timestamp absent from that evidence.

## Consequences

- Fabricated quotes and timestamps are structurally impossible on the two hardest requirements, which
  is what makes the "hallucination control" claim testable instead of rhetorical.
- The theme and disagreement rules are explicit and reviewable, but they are tuned to this guide: six
  questions mapped to six topics. Beyond ~30 transcripts this becomes a supervised classifier or
  embedding clustering, with the same quote citation layer underneath.
- Wording of the extracted quote is the expert's, not the analyst's, so guide answers read verbatim in
  no-key mode. That is a feature for this brief, and the optional summary layer only exists to make it
  read better.
