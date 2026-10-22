# Project Overview

## 1. The problem

Users report a specific, recurring experience: an AI model gives a technically
correct, knowledgeable answer that is nonetheless hard to learn from. The
complaint is not about accuracy or intelligence. It is about transfer.

The documented symptoms (see `RESEARCH_FOUNDATIONS.md` §1 for sources and
evidence levels) are concrete enough to work with:

- several ideas compressed into one sentence
- terminology used before it is defined
- indirect, nominalised phrasing where a direct sentence would do
- pronouns and demonstratives with no clear referent
- prerequisites assumed rather than supplied
- definitions without mechanism — *what* without *how* or *why*
- formatting that does not reflect the conceptual structure
- and, when asked to "explain simply", output that becomes patronising without
  becoming more understandable

That last one matters most. It means the obvious fix does not work, which is
why this project exists at all.

## 2. What we are actually measuring

**Explanation quality is not factual correctness, reasoning ability, writing
elegance, answer length, or visual polish.** It is how effectively an
explanation moves understanding from the system to the reader.

A good explanation lets the reader:

1. understand each statement,
2. follow the progression,
3. build a mental model,
4. understand the mechanism,
5. connect it to what they already know,
6. remember the principle,
7. apply it to a case the explanation did not cover,
8. without acquiring a misconception.

Item 7 is the real test, and item 8 is the one most easily missed: a
simplification can raise comprehension scores on the material while installing
a wrong model of it.

## 3. The research question

> Can a model's explanatory effectiveness be improved by an explicit,
> model-independent pedagogical transformation process, without retraining the
> underlying model?

And, if so: **which mechanism is doing the work?** Vocabulary? Sequencing?
Mechanism detail? Examples? Formatting? Audience matching? The point of the
platform is to separate these, because "rewrite this more clearly" is not a
finding.

## 4. Objectives

| Objective | How the platform meets it |
| --------- | ------------------------- |
| Compare models' default explanation behaviour | Experiment 1, with provenance and control limitations recorded |
| Test whether prompting is sufficient | Experiment 2, three required conditions, versioned prompts |
| Isolate which mechanism works | Experiment 3, six bounded treatments applied one at a time |
| Separate method from transformer capability | Experiment 4, full generator × transformer grid |
| Measure actual human understanding | Experiment 5, blinded allocation and graded assessment |
| Not fool ourselves | Four evidence classes kept structurally separate; no composite score |
| Keep it affordable | Pre-flight estimates, request ceiling, spend cap, response cache |
| Make it reusable later | The transformation engine has no framework dependencies in its core |

## 5. Product roadmap

**Stage 1 — ExplanationLab research platform. ← this implementation.**
A full-stack application for comparing explanations, experimenting with
pedagogical transformations, and measuring effectiveness.

**Stage 2 — Claude Skill.** Package the techniques that ExplanationLab shows to
work as an installable Skill, so a model communicates more understandably
without losing technical depth.

**Stage 3 — Explanation engine.** If instruction-level approaches prove
insufficient, extract the pipeline into a reusable service that analyses,
restructures and improves responses independently.

**Stage 4 — Universal browser extension.** Improve explanations across multiple
AI chat interfaces.

Stages 2–4 are **not implemented**. The MVP is organised so they can be:
`apps/api/explanationlab/transformations/` and `evaluation/` hold the strategy
definitions, schemas, stage logic and fidelity checks with no FastAPI or
SQLAlchemy imports in their core. The only platform coupling is a
`call_structured` callable passed in by the caller. Lifting the engine out means
replacing that one function, not untangling a web app.

Note the sequencing is deliberate: the Skill in Stage 2 should encode mechanisms
that *measured* better, not mechanisms that sounded plausible. Building the
instrument first is the whole point.

## 6. Scope boundaries

### In scope

- OpenAI and Anthropic via their official SDKs, with runtime-verifiable model
  catalogues
- Manual import of answers pasted from consumer chat interfaces, recorded as
  distinct provenance
- Text explanations
- A single local researcher, or a small trusted team behind a shared token
- Exploratory sample sizes, honestly labelled as such

### Out of scope

- Any claim about a provider's training process. We have no access to one.
- Multimodal explanations, voice, or interactive tutoring dialogue
- Public participant recruitment, panels, or incentive handling
- Multi-tenant accounts, roles, or organisational permissions
- Automated delayed-retention reminders (the schema supports reassessment; the
  scheduling does not exist)
- Significance testing. See `RESEARCH_FOUNDATIONS.md` §2 and `analytics/stats.py`:
  with realistic sample sizes, intervals communicate precision without inviting
  a decision the data cannot support.

## 7. Who this is for

A solo researcher or a very small team who wants to run real, reproducible
experiments on explanation quality without a lab, a grant, or a cluster. Every
engineering decision favours *a maintainer reading this in six months* over
architectural ambition: one gateway for model calls, one short component file,
a job queue that is a database table, and statistics implemented in the
standard library.

## 8. Principles the code actually enforces

These are not aspirations in a document; each one is implemented somewhere
specific.

1. **Understanding over appearance** — presentation (T5) is a separable
   treatment precisely so its effect on *perceived* clarity can be distinguished
   from its effect on comprehension.
2. **Explanation over simplification** — every treatment prompt forbids dropping
   technical content, and Stage D flags information loss and length collapse.
3. **Pedagogy over prompt decoration** — Condition C specifies a teaching
   process, not a writing style.
4. **Reproducibility over anecdotes** — responses are immutable and store the
   exact rendered prompt; prompt edits create versions.
5. **Human understanding over AI judge opinions** — judge output is stored as
   `ai_judge_opinion` and can never be aggregated into a comprehension figure.
6. **Model independence** — the transformation model is configured separately
   from the source model, always.
7. **Research before product claims** — no scoring path contains a model-identity
   term; the judge is blinded and answer order randomised.
8. **Reusability** — the engine core has no web-framework dependencies.
