# User Guide

How to run each of the five experiments, end to end.

---

## Before you start

```bash
bash scripts/setup.sh
```

Then two terminals:

```bash
# API
cd apps/api
./.venv/Scripts/python.exe -m uvicorn explanationlab.main:app --reload   # Windows
./.venv/bin/python -m uvicorn explanationlab.main:app --reload           # macOS / Linux

# web
cd apps/web && npm run dev          # or PORT=3100 npm run dev
```

Open <http://localhost:3000>.

### Demo mode first

With no API keys, everything works and nothing is billed. Generated
explanations are local fixtures flagged `SYNTHETIC`. Walk through the whole
workflow this way once — it costs nothing and the screens behave identically.

The demo fixtures deliberately illustrate the stylistic contrast under study: a
terse system prompt yields the dense, indirection-heavy style, the generic tutor
prompt yields the over-simplified style, and the pedagogical prompt yields the
scaffolded style. That is a *scripted illustration of the hypothesis*, never
evidence for it.

### Going live

Add to `.env` and restart the API:

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

The header badge changes from **Demo mode** to **Live**. Start with one
question, two models, one replicate.

### Set a token if anything but you can reach the machine

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Put it in `.env` as `RESEARCHER_API_TOKEN`, restart both processes. Until you
do, the API accepts **local requests only** — it does not run open.

---

## Experiment 1 — Baseline comparison

**Question it answers:** how do these models explain this, by default?

1. **Experiment studio** → choose **Experiment 1 · Baseline comparison**.
2. **Research questions** — select one to start. Note each question's
   conceptual difficulty: compare conditions *within* a question rather than
   averaging across questions of different difficulty.
3. **Models** — pick one OpenAI and one Anthropic model.
4. **Audience** — choose a learner profile. For a pure baseline you can leave it
   as *None*; it is still recorded.
5. Leave temperature empty. If you set it and a selected model rejects it, an
   amber warning appears telling you the conditions will not be
   temperature-matched. That is accurate — see §0.3 of `EXPERIMENT_DESIGN.md`.
6. **Record keeping** — write the objective and hypothesis now. They go into the
   report, and stating a hypothesis before the run is what lets the result
   disconfirm it.
7. **Estimate cost and request count.** The run button stays disabled until you
   do.
8. **Create and run experiment.**

You land on the experiment page, which polls while the batch runs. A failed run
does not stop the batch; it records its error and a **Retry failed runs** button
appears, which re-runs only the failures.

### Reading the result

**Comparison** workspace → pick your question → both answers appear side by
side, rendered by the same renderer so formatting cannot masquerade as content.

- **Rendering** — *Rendered* for normal reading, *Raw* to see exactly what the
  model emitted, *Distraction-free reading* to judge readability without
  surrounding chrome.
- **Automated diagnostics** — word count, average sentence length, long-sentence
  share, jargon candidates, indirection phrases, unresolved references, causal
  marker density, checklist coverage. These *describe* the text. They do not
  measure understanding, and shorter sentences do not mean a better explanation.
- **Control limitations** — expand this. It states which requested controls the
  provider would not honour.
- **Annotations** — record what you notice: a dense paragraph, an undefined term,
  a missing step. Qualitative observations are the lead for the next experiment.

### Importing a real web-chat answer

API output is **not** the same system as the ChatGPT or Claude consumer app.
Use **Import a web-chat answer** to paste a real response. It is stored with
`origin = manual_import`, the interface type, the capture time, and an explicit
limitation saying the settings and system prompt are unknown and not
API-comparable. Keep that distinction when you interpret it.

---

## Experiment 2 — Prompt intervention

**Question it answers:** is prompting alone enough?

1. **Experiment studio** → **Experiment 2 · Prompt intervention**.
2. Select questions — ideally 3–5, the same set across conditions.
3. Select **one** source model to start, so you are varying only the prompt.
4. All three prompt conditions are preselected. All three are required; the API
   refuses a configuration missing one.
5. Select a learner profile. Condition C uses it directly, so this matters.
6. Estimate, then run.

With 5 questions × 3 conditions that is 15 calls.

### What to look at

On the experiment page → **Results**: per-condition diagnostics with intervals,
and a metric selector. Then **Comparison**: read a Condition A answer beside a
Condition C answer for the same question.

Watch for the specific failure mode: Condition B ("explain simply") producing
output that is shorter and friendlier but no more informative. The diagnostics
will show fewer long sentences; whether anyone understood more is a question
only Experiment 5 can answer.

### Editing a prompt

**Library** → **Prompt templates** → **New version**. Earlier versions are
immutable and every response stores the prompt it was actually generated from,
so editing cannot rewrite a completed experiment's record. Write a changelog —
you will want it later.

---

## Experiment 3 — Ablation

**Question it answers:** which mechanism actually does the work?

1. **Experiment studio** → **Experiment 3 · Mechanism isolation**.
2. Select questions and one source model.
3. **Treatments** — load the preset *Each treatment alone*, or build your own.
   Expand *What each treatment does, and what it must not do* before choosing;
   the boundaries are the design.
4. Keep **Include an untransformed control arm** on. Without it an improvement
   cannot be distinguished from the baseline.
5. Decide on the pipeline stages. Keep **Stage D — fidelity verification** on;
   a transformed variant you have not audited is not safe to use as a stimulus.
6. Estimate — this is where the cost shows up. Each transformed run is
   1 generation + 1 analysis + 1 planning + N treatments + 1 fidelity.
7. Run.

### Reading the result

Experiment page → **Results** gives per-condition diagnostics and the fidelity
verdict distribution.

Then **Transformation workbench** on one answer to see the mechanics:

- **Per-treatment changes** — each step's before/after, measured statistics and
  unified diff. This is the attribution that applying treatments one at a time
  buys you.
- **Fidelity audit** — each warning is badged `deterministic` or `llm_reviewer`.
  Trust the first kind more: it is a reproducible rule you can verify by hand.
- **Pipeline stages** — the token and cost cost of each stage.

**Check for boundary violations.** If T1 added headings, the audit flags it, and
that variant is not a clean single-treatment condition — exclude it from strict
ablation analysis rather than reporting it as T1's effect.

### Results page

**Results** → group by **Treatment** to compare across everything you have run,
and see **Cost and latency per technique** for what each one costs.

---

## Experiment 4 — Cross-model transformation

**Question it answers:** is the improvement from the method, or from the
transforming model?

1. **Experiment studio** → **Experiment 4 · Cross-model transformation**.
2. Select **two or more source models**.
3. Select **two or more transformation models** — ideally the same two, so you
   get the full grid.
4. Choose a treatment set (all treatments combined is a reasonable start).
5. Keep the control arm on.
6. Estimate carefully: the grid multiplies. 2 generators × 2 transformers ×
   1 treatment set × 2 questions, plus controls, is already 40+ calls.
7. Run.

### Reading the result

Compare the four cells:

| Generator | Transformer | What a gain here means |
| --------- | ----------- | ---------------------- |
| A | A | Could be method, could be a second pass by a capable model |
| A | B | Method transfers across providers |
| B | A | Method transfers in the other direction |
| B | B | Same ambiguity as the first row |

If improvement appears in **all four**, the methodology is doing work. If only
where a particular model transforms, the transformer is doing the work. If only
on one diagonal, there is an interaction.

For a single ad-hoc cross-model pass, the **Transformation workbench** shows a
*Cross-model* notice when the transformer differs from the source, with the same
caveat.

---

## Experiment 5 — Blind human comprehension testing

**Question it answers:** did anyone actually understand more?

This is the only measurement in the platform that is evidence of comprehension.

### Build the study

1. **Human evaluation** → **New study**.
2. Name it, and pick the research question.
3. **Conditions** — select two or more variants. They must all answer the same
   question; the API refuses otherwise, because arm differences would be
   confounded with item difficulty. A good first study: one untransformed
   baseline against one transformed variant.
4. **Seed** — leave the default unless replicating. The allocation sequence
   replays from it.
5. **Balance arms** on, **Ask prior knowledge** on.
6. **Assessment items** — the template gives you one per comprehension
   dimension. Edit all three:
   - **Multiple choice (A)** — write real distractors. Tag any distractor that
     reveals a *specific* misconception with the **misconception** checkbox; that
     is what the misconception rate counts.
   - **Short answer (B)** — ask for the mechanism in their own words.
   - **Scenario (C)** — this is the important one. Describe a situation the
     explanation did **not** cover. Transfer is the real test of understanding;
     an item answerable by recall tests memory instead.
7. You do not need items for clarity (D) or effort (E) — they are collected on
   every submission automatically.
8. **Create study**, then **Open for participants**.

### Share the link

Study page → **Setup** → copy the participant link. It is an unguessable token
that grants assessment access only; it cannot reach any researcher endpoint.

Preview it yourself first. You will see: consent → optional prior knowledge →
read the explanation → questions → two ratings → thank you. Nothing identifies
the condition, the model, or the treatment.

If a link leaks, **Rotate token**.

### Grade

Study page → **Grading**.

Objective items are already scored. Free-text answers wait for you.

**AI-assisted grading** is available: pick a model, and suggestions appear
beside each free-text field with a rationale. They are suggestions. They sit in
a separate column and **cannot become the final score** — you type a number.
Use them to speed up a pass, not to replace it.

Grade against the rubric, not against your own phrasing: accept a correct answer
worded differently. Tick **misconception** when an answer reveals a confidently
wrong model of the mechanism — a blank or vague answer is not a misconception.

### Read the results

Study page → **Results**.

- **Comprehension score** is the primary evidence. Participants with ungraded
  items are excluded and the count is stated, so a partially-graded study cannot
  report a number as though complete.
- **Perceived clarity** and **cognitive effort** are shown separately and are
  never folded in.
- **Perceived clarity against measured comprehension** — the scatter plot.
  A condition high on clarity and low on comprehension is the
  illusion-of-fluency pattern: it felt easy and taught less. That is a finding,
  and it is exactly what a blended quality score would hide.
- **Read these first** — the warnings panel. At small n the intervals are wide
  and the study is labelled exploratory. Believe the label.

---

## Running the LLM judge

Available from the **Comparison** workspace (per response) or in bulk.

The judge is blinded: it never receives the provider, model id, condition label
or treatment names. Presentation order is randomised under a recorded seed, and
the rubric is anchored at 1/3/5 so it has something to calibrate against.

Configure it **independently of the models under test**. A cheap model
(`gpt-6-luna`, `claude-haiku-5-5`) is adequate and keeps a bulk pass affordable.

Judge output is stored as `ai_judge_opinion` and can never be aggregated into a
comprehension figure. It is useful for triage across many responses — not for a
conclusion.

---

## Exports and reports

From an experiment or study page:

| Format | Contains |
| ------ | -------- |
| **CSV** | One row per response (or per submission), with diagnostics, judge means, fidelity verdict, tokens, cost, latency, provenance. Carries a synthetic-data banner when applicable |
| **JSON** | Full reproducible record: configuration, conditions, questions with checklists, runs with errors, responses with prompt snapshots and limitations, evaluations, fidelity reports |
| **Markdown** | Human-readable report: objective, hypothesis, conditions, dataset, methodology, results with intervals, limitations, researcher notes |

**Generate report** persists it and marks the experiment *reported*.

The report's **Notable findings** section is left for you. The platform does not
generate conclusions from your numbers, by design.

---

## Managing the model catalogue

**Library** → **Model catalogue**.

Each entry carries a capability record. The **Temperature** column is the one to
look at: *rejected* means sending that parameter fails, so a
temperature-controlled condition is not available on that model.

**Refresh from providers** asks each configured provider for its live model
list, confirms what exists, flags catalogue entries the provider no longer
lists, and adds newly discovered models **disabled**, without pricing, with
conservative capability flags. Review and enable before use.

Prices are an operator-configurable estimate. Edit them if your rates differ,
and check your provider dashboard for authoritative billing.

---

## Troubleshooting

| Symptom | Cause and fix |
| ------- | ------------- |
| "Could not reach the ExplanationLab API" | The API is not running. Start it in `apps/api`. |
| Port 3000 in use | `PORT=3100 npm run dev`. Check nothing else is already serving 3000 — a stale server returns 200 for every path and looks like your app. |
| HTTP 402 / "Daily spend cap reached" | Raise `DAILY_SPEND_CAP_USD` in `.env`, restart the API. |
| HTTP 409 on **Run** | That exact batch is already queued, or every run already succeeded. Completed records are never regenerated. |
| "needs N model calls, over the limit" | Reduce questions, conditions or replicates, or raise `MAX_BATCH_REQUESTS`. |
| Everything says SYNTHETIC | Demo mode. Add an API key to `.env` and restart the API. |
| Batch stuck at 0 progress | `RUN_WORKER_IN_API=false` without a worker. Start `python -m explanationlab.jobs.worker`, or set it back to `true`. |
| Model returns 400 about a parameter | The adapter strips it, records a control limitation, and retries once. Check *Control limitations* on the response. |
| Study arm shows no results | Participants with ungraded free-text items are excluded. Grade them. |
| Participant sees "already completed this study" | Repeat exposure is blocked on purpose. Use a fresh browser session or a new participant code. |
