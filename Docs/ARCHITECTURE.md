# Architecture

## 1. Shape

```
┌──────────────────────────────────────────────────────────────────┐
│  Browser                                                         │
│  ┌────────────────────────────┐   ┌──────────────────────────┐   │
│  │ Researcher workbench       │   │ Participant assessment   │   │
│  │ /studio /compare /analysis │   │ /p/[token]               │   │
│  │ /transform /studies ...    │   │ (no researcher chrome)   │   │
│  └────────────┬───────────────┘   └───────────┬──────────────┘   │
└───────────────┼───────────────────────────────┼──────────────────┘
                │  fetch /api/proxy/*           │
┌───────────────▼───────────────────────────────▼──────────────────┐
│  Next.js server (apps/web)                                       │
│  app/api/proxy/[...path]/route.ts                                │
│    • attaches RESEARCHER_API_TOKEN server-side                   │
│    • WITHHOLDS it for p/* paths                                  │
│    • token and API address never enter the client bundle         │
└───────────────┬──────────────────────────────────────────────────┘
                │  HTTP
┌───────────────▼──────────────────────────────────────────────────┐
│  FastAPI (apps/api)                                              │
│                                                                  │
│  routers/        health · catalog · experiments · responses      │
│                  studies · analytics  [require_researcher]       │
│                  participants         [study token only]         │
│         │                                                        │
│  ┌──────▼────────────────────────────────────────────────────┐   │
│  │ gateway.py — THE single doorway for every model call      │   │
│  │   spend cap · response cache · usage records · cost       │   │
│  │   structured-output parsing with one repair retry         │   │
│  └──────┬────────────────────────────────────────────────────┘   │
│         │                                                        │
│  providers/   base (capability reconciliation) · openai ·        │
│               anthropic · demo (fixtures) · registry · catalog   │
│                                                                  │
│  transformations/  stages A–E · six treatments · fidelity        │
│  evaluation/       metrics · rubrics · blinded judge · grading   │
│  concepts/         graph validation · toposort · sequencing      │
│  experiments/      condition expansion · estimation · execution  │
│  studies/          seeded allocation · scoring                   │
│  analytics/        bootstrap statistics · aggregation            │
│  reports/          CSV · JSON · Markdown                         │
│  jobs/             durable queue (a table) + thread worker       │
└───────────────┬──────────────────────────────────────────────────┘
                │  SQLAlchemy 2.0
        ┌───────▼────────┐
        │ Postgres       │  (or SQLite for zero-setup local use)
        └────────────────┘
```

## 2. Decisions worth defending

### Sync SQLAlchemy, not async

FastAPI runs `def` endpoints in a threadpool, which is ample for a single
researcher's workload. Async SQLAlchemy would add real complexity — session
scoping across tasks, async migrations, two parallel driver stacks — in exchange
for concurrency this application never needs. Provider latency, not database
throughput, is the bottleneck, and the job worker handles that with threads.

### The job queue is a database table

Not Celery, not Redis, not RQ. The brief asks for "a minimal, reliable job
system" without "unnecessary distributed infrastructure", and for one researcher
a `jobs` table plus a polling thread is both. What it buys:

- **Durable** — a restart mid-batch loses nothing.
- **Resumable at the right granularity** — progress is tracked per *run*, not per
  job, so a retried job skips runs that already succeeded.
- **Idempotent submission** — `idempotency_key` is unique and derived from the
  exact pending run set, so a double-clicked **Run** cannot start two batches
  while a genuine later retry of new failures still works.
- **Multi-worker capable** — `claim_next` uses `FOR UPDATE SKIP LOCKED` on
  Postgres.

It runs in-process by default (`RUN_WORKER_IN_API=true`) and standalone via
`python -m explanationlab.jobs.worker` when you want it separate.

### One gateway for every model call

`gateway.call_model` is the only place a provider is invoked. Everything that
must not be bypassable lives there: the daily spend cap, the deterministic
response cache, token/cost/latency/error accounting into `usage_records`, and
synthetic-provenance propagation.

The payoff is that "review API costs, errors and generation metadata" is
answerable from the database rather than from log scraping — and that no future
feature can accidentally make an unmetered call.

### Capability records instead of a model allowlist

Model IDs go stale and capabilities change between generations. Rather than
hardcoding a list forever:

- the seed catalogue records *capabilities*, not just names
- `POST /api/models/refresh` asks each provider for its live model list, marks
  what it confirms, flags catalogue entries the provider no longer lists, and
  adds newly discovered models **disabled**, without pricing, with conservative
  capability flags
- `BaseProvider.reconcile_settings` drops unsupported parameters and returns a
  human-readable limitation note
- if a provider rejects a parameter anyway, the adapter strips it, records the
  fact, and retries once

A retired model therefore surfaces in the library, not as a mid-batch 404.

### Demo mode as a first-class provenance, not a stub

With no credentials, `registry.get_provider` returns a `DemoProvider` that
announces itself on every result. `is_synthetic` then propagates onto the
response row, every derived transformation, every evaluation, every usage
record, and every aggregate — and surfaces as a `SYNTHETIC` badge and report
banner. Demo data cannot be laundered into a results table because the flag
travels with the data rather than being inferred from configuration at render
time.

### Markdown rendered as React elements

`lib/markdown.tsx` parses to a block list and constructs React elements. No
`dangerouslySetInnerHTML`, no HTML sanitiser. Every string rendered here is
model-generated text from an untrusted pipeline, and "we build elements and
React escapes text" is a stronger guarantee than "we sanitise HTML and hope the
sanitiser is complete". Links are made clickable only for `http(s)`; anything
else renders as plain text.

## 3. Data flow: a baseline run

```
POST /api/experiments/estimate
  build_conditions → validate models and prompts → estimate cost and calls
POST /api/experiments
  expand conditions → one ExperimentRun per (condition × question × replicate)
  → status: configured
POST /api/experiments/{id}/run
  cost confirmation gate → enqueue Job (idempotency key over pending runs)
  → status: running

worker
  for each pending run:
    prompts.render(version, question, profile)      # question wrapped untrusted
    gateway.call_model(...)                           # cap, cache, usage, cost
    Response row (immutable, with prompt snapshots and limitations)
    metrics.compute_metrics → TextMetrics
    if condition.treatments:
        TransformationPipeline.run                    # stages A–E
        Response row (kind=transformed, parent_response_id=source)
        FidelityReport
  refresh_experiment_status → completed / failed
```

Note the ordering guarantee: a run marked `succeeded` with existing responses
returns the existing response instead of generating a second one, so re-running
is safe (`test_rerunning_a_succeeded_run_does_not_duplicate_work`).

## 4. Data flow: a participant submission

```
GET  /api/p/{token}            → consent screen only; no explanation yet
POST /api/p/{token}/enter      → check_repeat_exposure
                                 choose_condition (seeded, balanced)
                                 item_order_for (MCQ before free text)
                                 participant_view  ← ALLOW-LIST
POST /api/p/{token}/submit     → score objective items
                                 free text stored ungraded
                                 clarity and effort stored separately
POST /api/item-responses/{id}/grade   → human score becomes final
GET  /api/studies/{id}/results → per-arm comprehension + preference,
                                 bootstrap intervals, clustering warnings
```

## 5. Integration boundaries

### Provider boundary

Everything a provider needs is `GenerationRequest` → `GenerationResult`. The
rest of the platform never imports an SDK. Adding a provider means one adapter
class with `capabilities()` and `generate()`.

### Transformation engine boundary (the one that matters for Stages 2–4)

The engine's core — strategy definitions, JSON schemas, stage prompts, the
deterministic fidelity checks, the change-description statistics — imports no
FastAPI and no SQLAlchemy. `TransformationPipeline` takes a session only to pass
to `call_structured`, which is a plain callable.

To lift the engine into a Claude Skill, a standalone API or a browser extension,
you replace that one function with a direct SDK call. The treatments, the
boundaries, the schemas and the audit logic come across unchanged. That is what
Principle 8 means in practice.

### Participant boundary

Two separate dependency chains. `require_researcher` guards researcher routes;
the participant router has **no** researcher dependency, so a leaked study token
cannot reach researcher endpoints even by guessing a path. The payload boundary
is an allow-list, so adding a field to the `Response` model cannot accidentally
leak it to a participant.

## 6. Security posture

| Concern | Measure |
| ------- | ------- |
| Key exposure | Server-side only; never logged, never written to an experiment record; proxy keeps the token out of the client bundle |
| Open API | Bearer token required; with no token configured, non-local requests are refused rather than served |
| Token comparison | `secrets.compare_digest` — this token gates spend |
| Participant token scope | Assessment access only; different dependency chain |
| Prompt injection | Untrusted content wrapped in nonce-suffixed delimiters, forged closing tags neutralised with a zero-width character, guard instruction in the system prompt, length limits before any model sees the text |
| XSS from model output | React elements, never `innerHTML`; non-http links de-linked |
| Input limits | Enforced in Pydantic at the boundary, before anything reaches a prompt or the database |
| Runaway spend | Pre-flight estimate, batch ceiling, confirmation threshold, daily cap at the gateway |
| Duplicate submission | Unique idempotency key over the pending run set |
| Provider timeouts and retries | Configured per client; retries bounded; a failed run records its error and does not sink the batch |
| Participant privacy | Random codes, no personal data, withdrawal deletes |

Honest limits: the injection defence reduces risk rather than eliminating it; a
single shared researcher token is not per-user authentication; and there is no
rate limiting on participant endpoints. All three are recorded in
`KNOWN_LIMITATIONS.md`.

## 7. Technology choices

| Layer | Choice | Why |
| ----- | ------ | --- |
| Backend | FastAPI + Pydantic v2 | Validation at the boundary, generated OpenAPI |
| ORM | SQLAlchemy 2.0 typed mappings | Explicit, and Alembic autogenerate works |
| Migrations | Alembic, `render_as_batch` | One migration path for both Postgres and SQLite |
| Database | Postgres; SQLite fallback | Postgres for real studies, SQLite so a clone runs immediately |
| Frontend | Next.js 14 App Router | Server route handlers are what keep the token server-side |
| Data layer | TanStack Query | Polling a running batch and cache invalidation without hand-rolled state |
| Styling | Tailwind + ~15 local components | The whole visual system is one readable file |
| Graphs | React Flow (`@xyflow/react`) | Layered dependency layout; depth *is* teaching order |
| Charts | Recharts | Supports the error bars the statistics require |
| Statistics | Standard library | A bootstrap needs no scipy |
