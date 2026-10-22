# Manual Workflow — No API Key Required

How to run a real study with only ChatGPT Plus and Claude Pro ($20 web plans),
no paid API key. This answers the question: **why does ChatGPT's explanation
perform better, and what is the mechanism?**

> One thing to be clear about: the web apps are not the API. Their system
> prompts, memory and product scaffolding are unknown. Every manual import
> records this (`system_prompt_snapshot = "(unknown)"`). You are studying the
> *products*, which is exactly the right instrument for your question.

---

## What works without a key vs. what doesn't

| Works (real data) | Blocked (demo fixtures only) |
|---|---|
| Manual import of web answers | Automated generation / batch sweeps |
| Deterministic text metrics | Automated T1–T6 transformation pipeline |
| Full human comprehension study | Automated LLM judge (use Claude Code instead) |
| Statistics & exports | Cost / latency analysis |

---

## The experiment, stepwise

### 1. Pick questions (10–15)
Use the seeded questions (Library tab) or add your own. Keep them fixed across
both models. Spread across 2–3 domains.

### 2. Collect answers manually
For each question, ask it in **ChatGPT web** and **Claude web**. Start a fresh
chat each time (no memory carryover). Copy each full answer.

### 3. Import each answer
Comparison tab → *Import answer*, or `POST /responses/import`. Set:
- `question_id`, `provider` (openai / anthropic), `model_id` (e.g. `gpt-web`),
- `interface: web_chat`, `captured_at`, paste into `text`.

Imports are tagged `is_synthetic=false` — this is real data.

### 4. Compute metrics
`POST /responses/{id}/metrics` on each (or the Comparison tab button). Gives
readability, structure, indirection counts — deterministic, hand-checkable.

### 5. Code the pairs (this replaces the API judge)
Export the imported text (Results → export, or `exports.py`). Then paste the
**blinded** pairs into Claude Code (this terminal) and ask for structural
coding against the judge dimensions. No API key needed — the LLM judge is the
assistant you're already talking to.

### 6. Run ONE human study on the strongest contrasts
Studio → build a study from the two imported answers → open → take it via the
participant link. Recruit ~20 people (classmates, friends). This is your actual
comprehension evidence, not the metrics or the judge.

### 7. Read results
Results tab: comprehension and perceived clarity are reported **separately**,
never merged. The finding lives here.

---

## Turning the finding into a Claude skill

You don't need scale for this — you need mechanism. ~40 carefully read pairs
tell you *what* structural moves land; thousands only tell you *that* a gap
exists.

1. From steps 5–7, name the 2–4 concrete moves that track with better
   comprehension (e.g. prerequisite ordering, worked example before abstraction).
2. Write those as skill instructions.
3. Validate: hand-apply the skill to a weak answer, re-import, re-code (step 5),
   re-test (step 6). Confirm the moves actually improve comprehension.

---

## Honest limits

- Small n — pilot-scale, not population claims.
- Web system prompts unknown — you compare products, not raw models.
- Transformations are hand-applied, not pipeline-controlled.

None of these block the mechanism question. They do block large-scale automated
claims, which need an API key.
