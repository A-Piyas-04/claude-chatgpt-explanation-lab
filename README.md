# ExplanationLab

A research platform for measuring — and trying to improve — how well
AI-generated explanations actually transfer understanding to human readers.

It exists because of a specific gap: there is no widely adopted benchmark for
explanatory prose comparable to SWE-bench for code. Users report that models
can be technically excellent and still hard to learn from. ExplanationLab is
the instrument for testing whether that is true, what causes it, and what fixes
it.

**The core research question:** can a model's explanatory effectiveness be
improved by an explicit, model-independent pedagogical transformation process,
without retraining the model?

The platform is built so that question can be answered honestly — including
answered "no".

---

## What it does

Five experiments, all runnable end to end:

| # | Experiment | What it establishes |
| - | ---------- | ------------------- |
| 1 | **Baseline comparison** | How two models explain the same thing by default, with no tutoring prompt |
| 2 | **Prompt intervention** | Whether prompting alone closes the gap (default vs generic tutor vs structured pedagogical) |
| 3 | **Mechanism isolation** | Which of six transformation treatments actually works, individually and combined |
| 4 | **Cross-model transformation** | Whether an improvement comes from the method or from the transforming model |
| 5 | **Blind human comprehension testing** | Whether real people understood more. The only evidence that counts as comprehension |

Plus: a six-treatment transformation engine with factual-fidelity auditing,
concept dependency graph extraction, deterministic text diagnostics, a blinded
LLM judge, seeded randomised participant allocation, bootstrap uncertainty
estimates, and CSV/JSON/Markdown export.

### The one design rule worth knowing up front

**Four kinds of evidence are kept separate everywhere, and never averaged.**

1. **Automated diagnostics** — deterministic surface measures. Describe a text.
2. **AI judge opinion** — a judge model's rating. An opinion.
3. **Human preference** — participants' self-reported clarity and effort.
4. **Human comprehension** — measured learner performance.

This is not pedantry. Perceived ease of learning is known to dissociate from —
and sometimes invert against — actual retention. A transformation that makes an
explanation *feel* clearer while teaching *less* is a real and important
finding, and a blended "explanation quality score" would hide it. So there
isn't one, anywhere in the product.

---

## Quick start

Requirements: **Python 3.11+** and **Node 20+**. Docker is optional.

```bash
git clone <your-repo-url> explanation-lab
cd explanation-lab
bash scripts/setup.sh
```

Then, in two terminals:

```bash
# Terminal 1 — API
cd apps/api
./.venv/Scripts/python.exe -m uvicorn explanationlab.main:app --reload   # Windows
./.venv/bin/python -m uvicorn explanationlab.main:app --reload           # macOS / Linux

# Terminal 2 — web
cd apps/web
npm run dev
```

Open <http://localhost:3000>. If port 3000 is taken, use `PORT=3100 npm run dev`.

### It works with no API keys

With no credentials configured the app runs in **demo mode**: every generated
explanation comes from a local fixture, the full workflow is navigable, and
nothing is billed. Those rows are flagged `SYNTHETIC` for their entire
lifetime — the flag propagates into every transformation, evaluation, aggregate
and export, and is rendered as a warning wherever it appears. Demo output is
never presented as a research finding.

For live model calls, add a supported API key to `.env` and restart the API.
With only a Gemini key, Gemini can run analysis, transformation, and AI grading
on manually imported ChatGPT or Claude web answers; it cannot generate those
providers' answers. Follow [the real web-answer workflow](Docs/MANUAL_WORKFLOW.md).

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
```

### With Docker instead

```bash
cp .env.example .env     # add your keys
docker compose up        # Postgres + API + worker + web
```

Or just the database, running the app on the host:

```bash
docker compose up db
# then set DATABASE_URL=postgresql+psycopg://explab:explab@localhost:5432/explanationlab
```

---

## Commands

| Command | Does |
| ------- | ---- |
| `bash scripts/setup.sh` | Install everything, migrate, seed. Re-runnable. |
| `bash scripts/test.sh` | API tests, API lint, web typecheck, web production build. |
| `cd apps/api && .venv/.../python -m pytest -q` | Backend tests only (no network, no spend). |
| `cd apps/api && .venv/.../python -m explanationlab.seed` | Re-seed. Idempotent; never overwrites your prompt edits. |
| `cd apps/api && .venv/.../python -m alembic upgrade head` | Apply migrations. |
| `cd apps/api && .venv/.../python -m alembic revision --autogenerate -m "..."` | New migration after a model change. |
| `cd apps/api && .venv/.../python -m explanationlab.jobs.worker` | Standalone worker (set `RUN_WORKER_IN_API=false`). |
| `cd apps/api && .venv/.../python -m explanationlab.export_schemas` | Regenerate the shared TS contract. |
| `cd apps/web && npm run build` | Production web build. |

---

## First run: what to actually do

1. **Overview** — confirm the demo-mode banner matches what you expect.
2. **Experiment studio** → *Baseline comparison*. Pick a seeded question, select
   one OpenAI and one Anthropic model, and **Estimate** — the run button stays
   disabled until the cost is known. Then run it.
3. **Comparison** — read both answers side by side. Try the three rendering
   modes; *distraction-free reading* is the one to judge readability in.
4. **Transformation** — apply `T1` (vocabulary) and `T5` (presentation) to one
   answer. Look at *Per-treatment changes*: each step's effect is measured
   separately, which is the point of applying them one at a time.
5. **Fidelity audit** tab — note that a "clean" verdict says *no problem was
   detected*, not *verified accurate*.
6. **Pedagogical analysis** — extract a concept graph. Every edge is labelled a
   hypothesis, because an LLM-inferred prerequisite graph is one.
7. **Human evaluation** — build a study from the original and the transformed
   variant, open it, and take it yourself via the participant link. Nothing on
   that page reveals which arm you got.
8. **Grade** the free-text answer. An AI suggestion appears beside the field but
   cannot become the score — you have to type a number.
9. **Results** — see comprehension and perceived clarity reported side by side,
   never combined.

---

## Configuration

All settings live in `.env` (see `.env.example`). Highlights:

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `DATABASE_URL` | SQLite file | Postgres for real studies; SQLite needs no setup |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | empty | All empty ⇒ demo mode |
| `RESEARCHER_API_TOKEN` | empty | Empty ⇒ API accepts **local requests only** |
| `MAX_BATCH_REQUESTS` | 120 | Hard ceiling on model calls per experiment |
| `COST_CONFIRMATION_THRESHOLD_USD` | 1.00 | Batches above this need explicit confirmation |
| `DAILY_SPEND_CAP_USD` | 25.00 | The worker refuses new calls past this |
| `ENABLE_RESPONSE_CACHE` | true | Reuse identical deterministic requests |
| `RUN_WORKER_IN_API` | true | `false` ⇒ run the worker separately |

### Cost safety

API keys cost money, so the platform assumes you would rather be interrupted
than surprised: pre-flight estimates before every batch, a hard request
ceiling, explicit confirmation above a threshold, a daily spend cap enforced at
the gateway, a deterministic response cache (reuse is labelled), and
idempotency keys so a double-clicked **Run** cannot bill twice.

Cost figures are *estimates* from configured per-model prices and
provider-reported token counts. Check your provider's dashboard for real
billing.

---

## Project layout

```
explanationlab/
├── apps/
│   ├── api/                      FastAPI backend
│   │   ├── explanationlab/
│   │   │   ├── providers/         adapter layer + capability records
│   │   │   ├── prompts/           versioned templates + injection guard
│   │   │   ├── transformations/   the engine: stages A–E, six treatments
│   │   │   ├── evaluation/        diagnostics, rubrics, blinded judge
│   │   │   ├── concepts/          dependency graph validation + sequencing
│   │   │   ├── experiments/       orchestration and cost estimation
│   │   │   ├── studies/           allocation and scoring
│   │   │   ├── analytics/         statistics and aggregation
│   │   │   ├── reports/           CSV / JSON / Markdown export
│   │   │   ├── jobs/              durable queue + worker
│   │   │   └── routers/           HTTP surface
│   │   ├── alembic/               migrations
│   │   └── tests/                 unit, integration, end-to-end
│   └── web/                      Next.js frontend
│       ├── app/(workbench)/       researcher UI
│       ├── app/p/[token]/         participant UI (deliberately outside it)
│       └── app/api/proxy/         server-side token injection
├── packages/shared-schemas/      generated contract
├── Docs/                         documentation
├── scripts/                      setup.sh, test.sh
└── docker-compose.yml
```

---

## Documentation

| Document | Contents |
| -------- | -------- |
| [`Docs/PROJECT_OVERVIEW.md`](Docs/PROJECT_OVERVIEW.md) | Problem, objectives, roadmap, boundaries |
| [`Docs/RESEARCH_FOUNDATIONS.md`](Docs/RESEARCH_FOUNDATIONS.md) | Literature synthesis with evidence levels |
| [`Docs/EXPERIMENT_DESIGN.md`](Docs/EXPERIMENT_DESIGN.md) | Methodology, controls, scoring, reproducibility |
| [`Docs/ARCHITECTURE.md`](Docs/ARCHITECTURE.md) | Structure, data flow, integration boundaries |
| [`Docs/TRANSFORMATION_ENGINE.md`](Docs/TRANSFORMATION_ENGINE.md) | Every strategy, prompt, schema and fidelity check |
| [`Docs/DATABASE_SCHEMA.md`](Docs/DATABASE_SCHEMA.md) | Entities and relationships |
| [`Docs/USER_GUIDE.md`](Docs/USER_GUIDE.md) | Step-by-step for each experiment |
| [`Docs/MANUAL_WORKFLOW.md`](Docs/MANUAL_WORKFLOW.md) | Comparing ChatGPT and Claude web answers with a Gemini key and no participants |
| [`Docs/KNOWN_LIMITATIONS.md`](Docs/KNOWN_LIMITATIONS.md) | What this cannot do, and what is unfinished |

---

## Security

- Provider keys are read server-side only, never logged, and never written into
  an experiment record. The web app reaches the API through a Next.js route
  handler that attaches the researcher token server-side, so it never enters a
  client bundle.
- Researcher routes require a bearer token. With no token configured the API
  refuses non-local requests rather than running open.
- Participant links are unguessable tokens that grant assessment access only;
  researcher endpoints live behind a different dependency and are unreachable
  with one.
- Imported explanations, research questions and model output are treated as
  **untrusted data**: wrapped in forgery-resistant delimiters, with the system
  prompt instructing the model to treat them as material, never instructions.
  This reduces prompt-injection risk; it does not eliminate it.
- Model-generated Markdown is rendered by constructing React elements, never
  `innerHTML`, so no markup in model output can execute.
- Participants are identified by a random code. No name, email or IP address is
  collected. Withdrawal **deletes** the submission rather than flagging it.

---

## What this platform will not tell you

- That ChatGPT or Claude is the better teacher. No scoring path contains a
  model-identity term, and the judge is blinded.
- That an LLM judge measured understanding. It measured a model's opinion.
- That an inferred concept dependency graph is correct. It is a hypothesis.
- That demo data means anything at all.

Built to find the mechanism, not to confirm that we already knew it.
