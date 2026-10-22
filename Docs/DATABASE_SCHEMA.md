# Database Schema

29 tables. Source of truth: `apps/api/explanationlab/models.py`.
Migrations: `apps/api/alembic/versions/`.

---

## Two invariants the rest of the codebase relies on

### 1. Response rows are immutable

Once written, a `responses` row is never updated. A transformation produces a
**new** row with `parent_response_id` pointing at its source, so the chain from
raw model output through each variant is always reconstructible. Prompts are
snapshotted onto the row, so editing a template later cannot rewrite the record
of a completed experiment.

### 2. Synthetic provenance is sticky

`is_synthetic` is copied onto every derived row — transformations, judge
evaluations, fidelity reports, concept graphs, usage records — and computed into
every aggregate. Demo data cannot be laundered into a results table, because the
flag travels with the data rather than being inferred from configuration at
render time.

---

## Entity map

```
researchers                learner_profiles          research_questions
                                  │                        │
                                  │                        │
model_catalog        prompt_templates ──< prompt_versions   │
   (capability          (versioned, append-only)            │
    records)                      │                         │
                                  │                         │
transformation_strategies ──< transformation_versions        │
                                                            │
experiments ──< experiment_questions >────────────────────────┘
    │     ──< experiment_conditions ──┐
    │     ──< experiment_runs ────────┴──< responses (IMMUTABLE)
    │                                        │ parent_response_id (self-ref)
    │                                        ├──< text_metrics      (1:1)
    │                                        ├──< judge_evaluations
    │                                        ├──< fidelity_reports
    │                                        ├──< concept_graphs
    │                                        └──< annotations
    │
    └── (study_id optional link)
                 studies ──< study_conditions ──> responses
                       │ ──< assessment_items ──> grading_rubrics
                       └──< study_assignments ──< participant_submissions
                                                      └──< item_responses

jobs        response_cache        usage_records        research_reports
```

---

## Tables by area

### People and audiences

| Table | Purpose | Notes |
| ----- | ------- | ----- |
| `researchers` | Local researcher identity | Minimal; one row seeded |
| `learner_profiles` | Audience specification | `level`, `assumed_prior_knowledge[]`, `unfamiliar_with[]`. Doubles as the T6 treatment parameter. Four seeded, including a non-native-English-reader profile |

### Research questions

| Column | Why it exists |
| ------ | ------------- |
| `text`, `domain`, `topic` | Identification and filtering |
| `conceptual_difficulty` | Explicit, because questions are **not** equally hard — averaging across them mixes condition effect with item difficulty |
| `factual_checklist[]` | Reviewed essential claims. Drives coverage diagnostics and checklist-aware fidelity review |
| `checklist_reviewed_by` | Who reviewed it. Blank means "nobody", which the UI says |

### Models and providers

`model_catalog` — one row per selectable model, carrying a **capability record**
rather than just a name:

`provider` · `model_id` · `display_name` · `tier` · `input_cost_per_mtok` ·
`output_cost_per_mtok` · `context_window` · `supports_temperature` ·
`supports_effort` · `supports_max_output_tokens` · `supports_structured_output` ·
`default_effort` · `is_enabled` · `verified_live` · `last_verified_at` ·
`notes` · `pricing_source`

The capability columns are load-bearing, not documentation: current frontier
models *reject* `temperature` rather than ignoring it, so the adapter consults
this record before building a request. `verified_live` is set by
`POST /api/models/refresh` against the provider's live model list.

### Prompts (versioned, append-only)

`prompt_templates` → `prompt_versions` (unique on `template_id, version`).
Versions are never mutated. `experiment_conditions.prompt_version_id` and
`responses.prompt_version_id` reference a specific version, and the response
additionally stores the rendered text.

### Transformations (versioned)

`transformation_strategies` (T1–T6, each with a `boundary_note` recording what
the treatment must **not** do) → `transformation_versions` holding the
instruction template, input/output schemas and default parameters.

### Experiments

| Table | Grain | Notes |
| ----- | ----- | ----- |
| `experiments` | One per experiment | Lifecycle status, objective, hypothesis, seed, replicates, config blob with the pre-flight estimate, researcher notes |
| `experiment_questions` | Matched question set | Unique on `(experiment_id, question_id)` |
| `experiment_conditions` | One per experimental cell | Source provider/model, prompt version, learner profile, generation settings, **treatments**, and a **separate** `transform_provider` / `transform_model_id` |
| `experiment_runs` | One per (condition × question × replicate) | Unique on that triple — which is what makes retry-without-duplication structural rather than careful. Carries `status`, `attempts`, `error`, `error_type` |

The separate transformation-model columns are the schema-level expression of
Experiment 4's requirement: method and transformer must be independently
configurable or the confound is unresolvable.

### Responses (the central table)

Grouped by what each part is for:

**Identity and provenance** — `kind` (source / transformed), `origin` (api /
manual_import / demo_fixture), `run_id`, `parent_response_id`, `question_id`,
`learner_profile_id`, `prompt_version_id`, `provider`, `model_id`, `label`.

**Reproducibility** — `system_prompt_snapshot`, `user_prompt_snapshot`,
`requested_settings`, `generation_settings` (what was actually sent),
`control_limitations[]`.

The requested-versus-effective split is deliberate: it is how a dropped
`temperature` stays visible instead of looking like it was honoured.

**Content** — `text`, `applied_treatments[]`,
`transformation_version_ids[]`, `transformation_meta` (stage records, analysis,
plan, per-treatment change statistics and diffs).

**Accounting** — `input_tokens`, `output_tokens`, `latency_ms`, `cost_usd`,
`finish_reason`, `request_hash`, `served_from_cache`.

**Provenance flag** — `is_synthetic`.

### Analysis artefacts

| Table | Notes |
| ----- | ----- |
| `text_metrics` | 1:1 with a response. Full deterministic diagnostic payload plus `metrics_version` |
| `judge_evaluations` | Judge provider/model, rubric key and version, `blinded`, `presentation_order[]`, per-dimension `scores[]` with evidence and confidence, tokens and cost |
| `fidelity_reports` | Links transformed → source. `warnings[]` (each tagged with its detector), `numeric_drift[]`, `checklist_coverage[]`, `verdict`, `reviewed_by_human` |
| `concept_graphs` | `nodes[]`, `edges[]`, `teaching_order[]`, `cycles_detected[]`, and `is_hypothesis` hardcoded `True` |
| `annotations` | Manual researcher notes on explanation characteristics, with an optional quoted excerpt |

### Human studies

| Table | Notes |
| ----- | ----- |
| `grading_rubrics` | Keyed and versioned; `criteria[]` with score/label/descriptor |
| `studies` | Status, question, intro and consent text, seed, `balance_conditions`, `max_per_condition`, and a unique indexed `access_token` |
| `study_conditions` | One blinded arm → one response. `label` is **researcher-facing only** and never leaves the researcher API |
| `assessment_items` | Format, dimension, prompt, options, `correct_option_index`, `misconception_option_indexes[]`, rubric, max score |
| `study_assignments` | Anonymous `participant_code` (unique, indexed), condition, status, prior knowledge, `item_order[]`, `consented_at`, `withdrawn_at` |
| `participant_submissions` | 1:1 with an assignment. `reading_seconds` and `assessment_seconds` kept **separate**, plus `clarity_rating` and `cognitive_effort_rating` |
| `item_responses` | One per answered item |

### The scoring columns in `item_responses`

This is where the platform's firmest rule lives in the schema:

| Column | Written by |
| ------ | ---------- |
| `auto_score` | Objective matching on submission |
| `ai_suggested_score` | AI-assisted grading |
| `ai_rationale` | AI-assisted grading |
| `human_score` | A human grader |

```python
@property
def final_score(self):
    if self.human_score is not None: return self.human_score
    if self.auto_score  is not None: return self.auto_score
    return None
```

**`ai_suggested_score` has no path into `final_score`.** An AI grade cannot
silently replace human judgement in a research conclusion, because the
aggregation reads `final_score` and `final_score` cannot see it. Tested by
`test_human_score_wins_over_ai_suggestion`.

`rubric_version` is stored per grade, so a rubric revision does not retroactively
change what a score meant.

### Operations

| Table | Purpose |
| ----- | ------- |
| `usage_records` | Every model call: provider, model, purpose, tokens, cost, latency, success, `error_type`, `error_message`, cache reuse, experiment link, `is_synthetic`. This is what makes cost and error review a database query |
| `jobs` | Durable queue. `status`, `payload`, `attempts`, `max_attempts`, `progress_done/total`, and a unique `idempotency_key` |
| `response_cache` | `request_hash` primary key; stored text, tokens, `hit_count` |
| `research_reports` | Generated Markdown plus its data snapshot and `contains_synthetic_data` |

---

## Design choices

**Why JSON columns for metrics, scores and warnings.** These are
write-once-read-many analytical payloads whose shape is versioned
(`metrics_version`, `rubric_version`). Normalising them would add a dozen tables
and buy nothing, since no query filters on an individual metric — the
aggregation layer reads the payload and summarises in Python.

**Why `TextMetrics` is a separate 1:1 table rather than a column.** Diagnostics
are recomputable without a model call. Keeping them separate means
`POST /api/responses/{id}/metrics` can refresh them under a new metrics version
without touching the immutable response row.

**Why `study_conditions.label` exists at all** given participants must not see
it. Researchers need to know which arm is which; the separation is enforced by
the participant payload being an allow-list rather than by omitting the column.

**Why `experiment_runs` has a uniqueness constraint on its triple.** It makes
"retry failed tasks without duplicating completed records" a property of the
schema rather than something every call site must remember.

---

## Migrations

```bash
cd apps/api
python -m alembic upgrade head                                   # apply
python -m alembic revision --autogenerate -m "describe change"   # after a model edit
python -m alembic downgrade -1                                   # step back
```

Alembic runs with `render_as_batch=True`, so the same migration path works on
Postgres and on SQLite. The initial migration was verified to apply and roll
back cleanly across all 29 tables.

`create_all()` also exists, used by the SQLite fallback, the test suite and
first-run bootstrap. Alembic owns schema evolution for Postgres.
