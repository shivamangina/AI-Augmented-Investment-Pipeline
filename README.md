# AI-Augmented Investment Pipeline

A three-stage pipeline (Sourcing → Analysis → Recommendation) that turns a
topic query into one-page investment memos, built for the take-home in
[`Assignment.MD`](Assignment.MD).

```
python -m app.cli run --topic "AI agents for SMBs"
```

That's the whole interface. It writes `outputs/<topic-slug>/{candidates.json,
analysis/*.json, memos/*.html}` — all committed to this repo so you can read
the results without re-running anything. Start at
[`outputs/ai-agents-for-smbs/memos/index.html`](outputs/ai-agents-for-smbs/memos/index.html)
(open it in a browser — GitHub will render it as source, not as a page).

See [`PROCESS.md`](PROCESS.md) for how this was built and worked on with AI.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # then add your OPENAI_API_KEY
```

`OPENAI_API_KEY` is required for the analysis stage. `PRODUCTHUNT_API_TOKEN`
is optional — see `.env.example` for how to get a free one; without it,
Product Hunt sourcing is skipped with a warning and the pipeline still runs
end-to-end on YC + Hacker News.

## Running it

```bash
# Full pipeline, one command
python -m app.cli run --topic "AI agents for SMBs" --limit 15

# Re-render memos from already-committed analysis (no API calls at all)
python -m app.cli run --topic "AI agents for SMBs" --skip-sourcing --skip-analysis

# Serve the generated memos over HTTP instead of opening the files directly
uvicorn app.main:app --reload
# then browse http://localhost:8000/memos/ai-agents-for-smbs/memos/index.html
```

## Tests

```bash
pytest
```

No network access or API keys required — sourcing parsers and the OpenAI
call are tested against fixtures/mocks, not live APIs.

## The thesis

Defined once in [`app/thesis.py`](app/thesis.py) and used everywhere a score
or memo is produced (the analysis prompt, the memo template):

> We back startups building AI agents (or the infrastructure underneath
> them) that automate a specific, recurring, painful back-office or
> operational workflow for small-and-medium businesses — not consumer AI,
> not enterprise-only AI, not general foundation-model plays.

The final 0–100 score is a **weighted formula** over four LLM-produced
sub-scores (team 25%, product 30%, market 25%, risk-adjustment 20%) — not one
opaque number — so it's auditable: every memo shows the breakdown that
produced its score.

## Architecture

```
app/
  sourcing/       # YC directory + HN Algolia + Product Hunt -> candidates.json
  analysis/       # one structured OpenAI call per candidate -> analysis/*.json
  recommendation/ # deterministic Jinja2 render of analysis -> memos/*.html
  pipeline.py     # orchestrates the three stages — the only place they connect
  cli.py          # `python -m app.cli run --topic ...`
  main.py         # FastAPI wrapper around the same pipeline
```

Each stage writes its output to disk before the next stage starts, so the
pipeline is **replayable**: you can re-render memos from committed
`analysis/*.json` without an API key, or re-run only sourcing to refresh
candidates. Sourcing and analysis both degrade gracefully — a failing source
or a failing candidate analysis is logged and skipped rather than crashing
the run, since a partial memo set beats no memo set.

### Why these two sourcing choices stand out

- **YC directory** (`app/sourcing/yc.py`): pulls full batches from YC's
  public companies API and ranks client-side by keyword overlap with the
  topic (there's no server-side full-text search on that endpoint).
- **Hacker News** (`app/sourcing/hn.py`): the official Algolia Search API,
  used for both supplementary discovery (Show HN posts) and — more
  importantly — per-candidate traction enrichment (points/comments/date),
  which is the "freshness or traction signal" the assignment asks for.
- **Product Hunt** was kept as a third source at the cost of some of the
  assignment's "go deep on one or two" guidance; see `PROCESS.md` for that
  tradeoff and why it's built to fail open rather than block the pipeline.

### Traceability

Every `Candidate` carries `source_urls` — the exact pages the data came
from. The analysis prompt is instructed to use *only* that data, mark
missing fields as unknown instead of inventing them, and score missing data
as a real risk rather than a neutral gap. Every memo ends with a Sources
section listing those same URLs, so a claim in a memo can always be traced
back to where it came from.

## What's not built

Per the assignment's scope constraint: no job queue, no vector DB, no
frontend. Concurrency within a run uses plain `asyncio.gather` /
`Semaphore`, not a task queue. The FastAPI app exists because it was asked
for explicitly; it's a thin wrapper with no logic of its own, not a second
implementation of the pipeline.

## Repository access

Per the assignment: add `chiragmakkar` and `hari@emsoft.com` as
collaborators on the private GitHub repo before submitting.
