# ADR 0001 - In-memory corpus for v1, SQLite/FTS5 documented as the scaling step

**Status:** accepted (2026-09-22)

## Context

`docs/07-Database-Schema.md` (a local working note, not shipped in this repo) specifies nine SQLite
tables plus an FTS5 index. The corpus that actually
ships is three transcripts, roughly 42 turns and under 5 KB of text, all loaded from disk at startup.
The case asks for a "simple app" and warns that a bloated one is a red flag.

## Decision

Hold the parsed transcripts in memory in `app/main.py` and serve from there. Do not ship a database, a
repository layer or an ORM. Keep the SQLite/FTS5 schema in the docs unchanged, labelled as the answer
to "how would you scale this to 30+ transcripts".

## Consequences

- Startup re-parses the three files; no state to migrate, no file locking, and the demo can reset by
  restarting. Uploads add to the in-memory list and are lost on restart, which is acceptable for a demo
  and is stated in the README.
- No `sqlite3` connection handling, no schema versioning, no ORM, and no test fixtures for a database:
  the suite tests the parsing and analysis functions directly.
- The scaling path is a swap behind the same call sites, not a redesign: the route handlers and
  `app/analyze.py` signatures stay, `load_transcripts` becomes a repository read, and
  `lexical_search` becomes an FTS5 BM25 query. This is the one place where the docs and the shipped
  code intentionally differ, and it is stated rather than hidden.
