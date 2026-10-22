# Experiment Design

Methodology for the five experiments: conditions, controls, scoring, and what
makes a run reproducible.

---

## 0. Controls that apply to every experiment

### 0.1 What is recorded on every run

Stored on the `responses` row (immutable) and in every export:

experiment type · research question · topic and domain · learner profile ·
source provider · exact source model identifier · raw response text · prompt
template id **and version** · the **exact rendered system and user prompt** ·
transformation strategies and versions · transformation model · requested
generation settings · *effective* generation settings · randomisation seed ·
timestamp · token usage · estimated cost · latency · finish reason · cache
reuse · synthetic provenance · errors and retry count · control limitations.

The distinction between **requested** and **effective** settings is load-bearing;
see §0.3.

### 0.2 Reproducibility

- **Responses are immutable.** No row is ever updated after creation. A
  transformation produces a new row pointing at its parent, so the chain from
  raw model output to final variant is always reconstructible.
- **Prompts are versioned and snapshotted.** Editing a template appends a
  version; the response stores the rendered text. A later edit cannot rewrite
  the record of a completed experiment.
- **Seeds are recorded** for participant allocation, item ordering, judge
  presentation order and bootstrap resampling.
- **Raw outputs are stored**, so re-evaluation (new diagnostics, a different
  judge, re-grading) never requires re-calling a paid API.

What is *not* reproducible: provider inference itself. No current model
guarantees bitwise determinism, and the frontier models do not expose
temperature at all. Replicates (`repetitions > 1`) exist to measure that
variability rather than pretend it away, and are stored separately — the
response cache never deduplicates them.

### 0.3 The control limitation we cannot engineer away

The brief asks for "comparable, documented generation conditions". On current
frontier models this is **partly unachievable**, and that is a finding rather
than a bug.

Verified 2026-10-22: `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`
and OpenAI's `gpt-6-*` line **reject the `temperature` parameter**. It is not
ignored — the request fails. Thinking cannot be disabled on Opus 5.5; depth is
controlled by an `effort` level whose default differs per model.

So the classical lever for holding generation conditions constant does not
exist on the models most worth studying. The platform's response:

1. Each model carries a **capability record** (`supports_temperature`,
   `supports_effort`, `supports_max_output_tokens`,
   `supports_structured_output`, `default_effort`).
2. Unsupported parameters are **omitted, not substituted**, and every omission
   is recorded as a `control_limitation` string on the run.
3. Those strings surface in the comparison UI, the condition view, and every
   exported report.
4. If a provider rejects a parameter anyway, the adapter removes it, records
   that fact, and retries once — rather than failing the batch or silently
   switching model.
5. `gpt-5.4` is kept in the seed catalogue specifically because it *does* accept
   `temperature`, making a genuinely temperature-controlled condition possible
   when the design needs one.

A further deviation, applied identically in all conditions and recorded on every
response: a one-sentence prompt-injection guard is appended to the system prompt
even in the default condition, which is therefore not literally empty. This is a
security control we are not willing to drop; making it visible is the honest
alternative to hiding it.

### 0.4 Matched question sets and clustering

- Compare conditions **within** a question. Questions differ in conceptual
  difficulty — the seed bank records `conceptual_difficulty` explicitly for this
  reason — so averaging across them mixes condition effects with item difficulty.
- Observations are **clustered**. Several ratings of one response, or several
  answers from one participant, are not independent samples.
  `analytics/stats.independence_warnings` detects this and the warning travels
  with the numbers into the API payload, the results table and the report.

### 0.5 Cost controls

Pre-flight request count and cost estimate before any batch; a hard ceiling
(`MAX_BATCH_REQUESTS`); explicit confirmation above
`COST_CONFIRMATION_THRESHOLD_USD`; a daily cap enforced in the gateway;
a deterministic response cache whose reuse is labelled and billed as zero; and
an idempotency key derived from the exact pending run set, so a double-clicked
**Run** cannot bill twice while a genuine later retry still works.

---

## Experiment 1 — Baseline model comparison

### Objective
Characterise how models explain the same thing *by default*.

### Conditions
One arm per source model. Prompt condition is forced to the default template,
and the orchestrator **refuses** a non-default template here — adding a tutoring
instruction would contaminate the thing being measured.

### Procedure
1. The same question goes to every model.
2. Documented, comparable generation conditions where the providers allow it;
   limitations recorded where they do not (§0.3).
3. Responses generated independently, raw output stored.
4. Metadata captured; diagnostics computed automatically.
5. Results rendered side by side through an **identical renderer**, so
   formatting differences cannot masquerade as content differences.
6. Manual annotation of explanation characteristics is available per response.
7. Blinded evaluation is available via the judge and via Experiment 5.

### Provenance control
API output is **not** the same system as the ChatGPT or Claude consumer
interface: product-side system prompts, tools and scaffolding are invisible to
us. The manual-import path records `origin = manual_import`, the interface type,
capture time, and an explicit limitation stating that settings and system prompt
are unknown and **not** API-comparable.

### Deliverable
A baseline comparison report that does not assume either model is superior. No
scoring path contains a model-identity term.

---

## Experiment 2 — Prompt intervention

### Objective
Determine whether better prompting alone produces more understandable
explanations.

### The three required conditions

**A — Default.** No system prompt. Deliberately empty: any instruction here is
itself an intervention.

**B — Generic tutor.** *"Act as a helpful tutor. Explain clearly, step by step,
using simple language and practical examples."* Kept short on purpose — it must
represent ordinary prompting practice, not a straw man.

**C — Structured pedagogical.** Specifies a *teaching process* in ten steps:
infer the learner, identify prerequisites, establish the problem, order the
concepts, explain mechanism not just definition, ground abstractions, define
terms at first use, preserve technical accuracy, **do not patronise**, **do not
pad**.

The last two are negative constraints, and they are there because of a
documented failure mode: "explain simply" producing output that is
condescending without being clearer. A design that only asked for clarity could
not detect that it had made things worse.

The structure of C is itself the hypothesis: that naming the steps of
instructional design beats asking for clarity directly.

### Features
Template management, three-condition comparison, identical-question batch runs,
append-only version history, prompt parameter inspection, reproducible runs.
The orchestrator **requires** all three conditions to be present.

### Deliverable
Evidence on whether prompt instructions alone are sufficient. Bears on **H1**.

---

## Experiment 3 — Mechanism isolation / ablation

### Objective
Find out which specific technique does the work.

### The six treatments

| Key | Treatment | Does | Must not |
| --- | --------- | ---- | -------- |
| **T1** | Vocabulary and sentence clarification | Replace avoidable jargon, define necessary terms inline, split multi-idea sentences, resolve ambiguous references, remove indirection and padding | Reorder, add examples, add formatting, add mechanism, drop content |
| **T2** | Prerequisite-aware sequencing | Reorder so nothing precedes its prerequisites; add minimal bridging; name mutual dependencies | Simplify vocabulary, add examples, add formatting |
| **T3** | Mechanism and causal explanation | Make steps explicit, state causes, describe component interaction, separate cause/effect/precondition/exception | Invent a mechanism to fill a gap, simplify vocabulary, add analogies, reorder |
| **T4** | Concrete examples and analogies | One realistic example, mapped explicitly to the concept, with its breaking point stated | Use childish or patronising comparisons, add decorative examples, invent factual specifics |
| **T5** | Structural and visual presentation | Headings that state what a section establishes, short paragraphs, ordered steps, tables for real comparisons, a diagram spec for flows | Change wording, order or content; add structure for its own sake |
| **T6** | Audience adaptation | Introduce what this learner lacks, skip what they have, adjust unpacking depth | Change the facts, patronise, add examples |

### Why the "must not" column exists

Ablation is meaningless if the treatments are not separable. A "vocabulary only"
variant that also added headings and an analogy is not a vocabulary variant, and
a T1-vs-T2 comparison would measure nothing.

So boundaries are enforced in two independent places:

1. the instruction tells the model what not to do, and
2. **Stage D checks the output** — `check_boundary_violations` counts added
   headings, tables and list items on T1/T2/T3/T4/T6, and flags T5 if the word
   count moved more than 35% (presentation-only treatments should leave prose
   roughly intact).

A flagged variant is reported as not being a clean single-treatment condition
and should be excluded from strict ablation analysis. This is checked by test
(`test_vocabulary_treatment_adding_headings_is_a_boundary_violation`).

### Comparison conditions

Selectable: the original answer, each treatment individually, combined
treatments, and arbitrary researcher-defined combinations. An untransformed
control arm is included by default.

**Treatments are not forced on every explanation.** Stage B may conclude that a
particular explanation needs no analogy or no diagram, and records that
decision. A simple topic genuinely may not need one, and recording the refusal
is what makes the ablation interpretable.

### Composition order

When treatments combine, order is an uncontrolled variable unless fixed. The
canonical order is:

```
T3 (mechanism) → T4 (examples) → T6 (audience) → T1 (language) → T2 (sequencing) → T5 (presentation)
```

Content-adding treatments run first so later stages operate on the fuller text;
language polish precedes reordering; presentation is last. The order used is
recorded on every combined variant and can be overridden per condition.

### Implementation requirement

Each strategy is a versioned database row with a unique key, description,
boundary note, instruction template, input/output schema, configurable
parameters, recorded provenance and evaluation metadata. Treatments execute
independently and compose.

### Deliverable
An ablation report measuring which techniques work individually and together.
Bears on **H2** and **H3**.

---

## Experiment 4 — Cross-model transformation

### Objective
Determine whether an *external* pedagogical process can substantially improve
another model's answer.

### The confound this experiment exists to resolve

If Claude generates, Claude transforms, and the result is better, that could be
the methodology — or it could be that a second pass by a capable model helps
regardless of method. The design therefore requires the **full grid**:

| Generator | Transformer |
| --------- | ----------- |
| Claude | Claude |
| Claude | OpenAI |
| OpenAI | Claude |
| OpenAI | OpenAI |

Only with every cell can improvement be attributed to the methodology, the
transforming model, or their interaction. The transformation model is a
**separate configuration field** from the source model throughout the platform —
schema, API, and UI — not a convenience default.

### Procedure
1. Generate or import a source explanation.
2. Preserve the original (immutable row).
3. Apply the selected transformation.
4. Compare original with transformed.
5. Measure comprehensibility and factual fidelity.
6. Repeat across questions and learner profiles.

### Meaning preservation

The transformed explanation must not silently change technical claims, invent
contradicting examples, remove limitations, introduce unjustified certainty,
change formulas or numbers, or introduce false simplifications.

Stage D audits this in two independent layers (see `TRANSFORMATION_ENGINE.md`
§5). Critically, the deterministic layer **can escalate the LLM reviewer's
verdict but never soften it** — a model reporting "clean" does not clear a
detected numeric change. Verified by
`test_deterministic_checks_escalate_a_clean_llm_verdict`.

Automated factual checks are labelled `provisional: true` everywhere. A "clean"
verdict means *no problem was detected*, never *verified accurate*.

### Deliverable
A cross-model transformation comparison report. Bears on **H5**.

---

## Experiment 5 — Blind human comprehension testing

### Objective
Find out whether explanations help real people understand and apply concepts.

**Comprehension is never simulated with an LLM and reported as learner
evidence.** The platform has no code path that can do this: human comprehension
figures are computed only from `ItemResponse.final_score`, which returns a human
score or an objective auto-score, and never an AI suggestion.

### Workflow
1. Researcher creates a study from two or more variants.
2. Selects eligible variants — all must answer the **same question**, or the API
   refuses (otherwise arm differences are confounded with item difficulty).
3. Configures audience criteria and comprehension items.
4. Publishes a shareable participant link.
5. Participant enters, reads the consent notice, consents.
6. Optional short prior-knowledge self-report.
7. System assigns a condition.
8. Participant reads the explanation **without knowing its source**.
9. Participant completes the assessment.
10. Scores, reading duration and feedback are stored.
11. Researcher grades free text and reviews aggregates.

### Blinding, concretely

The participant payload is built by an **allow-list**
(`studies/assignment.participant_view`), not by filtering a full object. It
contains the explanation text, the items with answer keys removed, and nothing
else. Model identity, provider, condition label and treatment names are not
present in the data the browser receives — not merely hidden by the UI. A test
asserts that none of those strings appears anywhere in the payload.

The participant route also sits **outside** the researcher layout group in the
web app, so it inherits no navigation, no mode banners and no experiment
context. The proxy explicitly withholds the researcher credential from
participant paths.

### Allocation
- Randomised, seeded on `study.seed + study.id + participant_code`, so the same
  participant always lands in the same arm and the whole sequence replays.
- Balanced: least-filled arm first, with seeded tie-breaking. Arms are sorted
  before the draw so their database order cannot influence allocation.
- Optional per-arm cap.
- **Repeat exposure is blocked.** A participant who has already seen an
  explanation of this concept — in this study or another study on the same
  question — is refused, because seeing two explanations of one concept before
  assessment contaminates both measurements.

### Item ordering

Free-text mechanism and transfer items are always presented **after**
multiple-choice items. Writing an explanation in your own words is itself a
learning intervention (the self-explanation effect), so asking it first would
change the answers to everything after it. Within each block, order is
randomised by seed. Presentation order is stored per item response.

### Required dimensions

| | Dimension | How it is measured |
| - | --------- | ------------------ |
| A | Immediate comprehension | Multiple-choice, auto-scored |
| B | Mechanistic understanding | Short answer, rubric-graded by a human |
| C | Transfer | Scenario application, rubric-graded by a human |
| D | Perceived clarity | 7-point self-report, collected on every submission |
| E | Cognitive effort | 7-point self-report, collected on every submission |
| F | Misconception detection | Tagged distractors, plus grader judgement on free text |
| G | Time | Reading seconds and assessment seconds, measured separately |
| H | Delayed retention | Schema supports reassessment; **automated reminders are not implemented** |

**A/B/C are never averaged with D/E.** The fluency literature shows perceived
ease can move opposite to retention, so the platform reports
`human_comprehension` and `human_preference` as separate objects and the results
view plots them against each other explicitly. A condition that is high on
clarity and low on comprehension is a result, not an error.

### Question formats and grading

Multiple-choice, short answer and scenario application. Objective items are
scored on submission. Free text is left **ungraded** until a human grades it.

AI-assisted grading is available and writes to `ai_suggested_score` with a
rationale — a separate column from `human_score`. The `final_score` property
prefers human, then objective auto-score, and **never** returns an AI
suggestion. Aggregates exclude participants with ungraded items and say so, so a
partially-graded study cannot quietly report a number as if complete. The rubric
key and version are stored with every grade.

### Participant protection
Anonymous codes; no personal information collected; a plain-language consent
notice; withdrawal **deletes** the submission and its item responses rather than
flagging them; individual results are never exposed, only aggregates; no score
is returned to the participant, so a delayed-retention follow-up stays
interpretable and participants cannot compare notes.

### Deliverable
A human comprehension study report comparing the assigned conditions, with
intervals, clustering warnings and explicit exploratory-sample labelling.

---

## Scoring summary

| Measure | Range | Class | Computed by |
| ------- | ----- | ----- | ----------- |
| Surface diagnostics | varies | automated_diagnostic | `evaluation/metrics.py`, deterministic |
| Readability indices | varies | automated_diagnostic | deterministic — **never used to rank**; see `RESEARCH_FOUNDATIONS.md` §2 |
| Sequencing violations | count | automated_diagnostic | `concepts/graph.py`, deterministic given the hypothesised graph |
| Judge dimensions | 1–5 anchored | ai_judge_opinion | configurable judge model, blinded |
| Fidelity verdict | clean / warnings / serious_concerns | provisional | deterministic checks + LLM reviewer |
| Perceived clarity | 1–7 | human_preference | participant |
| Cognitive effort | 1–7 | human_preference | participant |
| Comprehension | 0–1 proportion | human_comprehension | human grades + objective auto-scores |
| Misconception rate | 0–1 | human_comprehension | tagged distractors + grader judgement |

## Evidence standard

A higher automated score, or a higher judge score, is **not** evidence that a
model teaches better. Every report distinguishes automated diagnostics, AI judge
opinions, human preference results and actual comprehension results, and states
which of them its claims rest on.

## Statistical reporting

- Means with 95% percentile-bootstrap intervals, seeded.
- **No interval below n = 8.** A bootstrap from four points produces a
  confident-looking range that means nothing, so the platform reports the
  descriptive numbers and declines the interval.
- n < 20 is labelled exploratory in the payload and in the report.
- Paired analysis available where the design pairs observations.
- Cohen's *d* available as a descriptive effect size.
- **No p-values.** At realistic sample sizes a significance test would invite
  exactly the overclaiming this platform is built to avoid.
