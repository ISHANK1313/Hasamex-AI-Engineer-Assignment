# Submission Plan — Manual vs Automated

| Field | Value |
|---|---|
| **Document** | What YOU do manually vs what I can handle |
| **Status** | Plan for the case submission |
| **Related** | [11-Checklist](11-Checklist.md), [13-Demo-Script](13-Demo-Script.md), [15-Run-Guide](15-Run-Guide.md) |

---

## 1. What you must do manually (no way around it)

| # | Task | Why you | Approx. effort |
|---|---|---|---|
| 1 | **Upload/fill the submission form** | It's on your portal; needs your account/sign-in | 10–15 min |
| 2 | **Record the demo video** (your face/voice — their instruction says "record a short demo video showcasing your application") | It's *your* interview; they want you presenting | 20–40 min |
| 3 | **Push the repo to GitHub** | The repository must be under an account they can share/verify; I can prepare everything but the push needs your credentials | 5–10 min |
| 4 | **Run the app locally once** (to show it and to capture screen footage) | Needs your machine, your terminal | 10 min |
| 5 | **Provide an API key if you want the optional LLM mode demoed** | Key is yours (env var only, never committed) — NOT required; app works without it | 2 min |
| 6 | **Make the final decision on stack (Python recommended)** | Quick confirm (one message is enough) | 1 min |
| 7 | **Submit the links** (repo URL, run instructions, video link) in their form | Manual form step | part of #1 |

## 2. What I can handle (automated / done here)

| # | Task | Deliverable / where |
|---|---|---|
| 1 | Full requirements + design docs | `docs/01..07` (PRD, TRD, Architecture, HLD, LLD, Request-Flow, DB Schema) |
| 2 | Memory, phases, thinking aid, checklist, cheat sheet | `docs/07-Memory`, `08-Phases`, `09-Scratchpad`, `10-Reference`, `11-Checklist`, `12-Fast-Lookup` |
| 3 | Readme for the repo (short, submission-ready) | `README.md` (root, next step) |
| 4 | Local run instructions | `docs-extra/15-Run-Guide.md` |
| 5 | Demo video script (word-for-word) | `docs-extra/13-Demo-Script.md` |
| 6 | Golden dataset + tests so accuracy is verifiable | `data/golden_dataset.json` + `tests/` (next step) |
| 7 | The working application (backend + UI) | `app/`, `static/`, `requirements.txt` (next step) |
| 8 | Scaffold `.env.example` and `.gitignore` so you can't leak the key | next step |
| 9 | Walk through and rehearse the demo storyline | this chat + `13-Demo-Script.md` |
| 10 | Fix bugs / iterate after you run it | on request |

## 3. Recommended order (to unblock quickly)

1. **You:** reply with the one-line stack + key decision (Python/FastAPI OK? no-key demo OK?).
2. **Me:** build the app, tests, README, run guide (everything turnkey).
3. **You:** `pip install -r requirements.txt` → `uvicorn app.main:app` → confirm it runs.
4. **Me:** polish + generate the demo script if you want tweaks after you've clicked through.
5. **You:** push to GitHub (I'll prepare messages), record video following the script, submit form.

> Split is honest: **I do engineering + documentation; you do identity-bound tasks** (record, push,
> submit). Everything else is designed so those three steps take under an hour total.

## 4. Submission checklist (final)

- [ ] Repo public (or private with view access set)
- [ ] README with: what it is, features, run instructions (2 commands), how accuracy is enforced
- [ ] Working app demonstrated in video
- [ ] Video covers: architecture, model choice, citations/timestamps, hallucination reduction, scaling 3→30+
- [ ] URL + video + run instructions submitted on their form