# Known Limitations

Written to be read before drawing a conclusion from anything this platform
produces. Nothing here is hidden in the UI; the limitations that affect a
specific number are surfaced next to that number.

---

## 1. Methodological limitations

### 1.1 Generation conditions cannot be fully matched

The single most important caveat. Verified against provider documentation on
2026-10-22: current frontier models (`claude-opus-5-5`, `claude-sonnet-5-5`,
`claude-haiku-5-5`, the `gpt-6-*` line) **reject the `temperature`
parameter** — the request fails rather than ignoring it. Reasoning depth is
controlled by provider-specific `effort` levels whose defaults differ per model
and are not comparable across providers.

So the classical lever for holding generation conditions constant does not exist
on the models most worth studying. The platform records every omission as a
`control_limitation` on the affected run and surfaces it in the UI and every
report, but **a cross-provider baseline comparison is not a controlled
experiment in the strict sense.** It is a comparison of two systems under their
own defaults, which is a legitimate and interesting thing to measure — but not
the same claim.

`gpt-5.4` is retained in the catalogue specifically because it still accepts
`temperature`, enabling a genuinely temperature-controlled condition when a
design needs one.

### 1.2 Provider inference is not reproducible

No current provider guarantees bitwise determinism. Replicates
(`repetitions > 1`) measure that variability rather than pretending it away, and
the response cache never deduplicates them. But an identical configuration on a
different day may produce different text, and providers update models silently.
Record dates; treat a result as a measurement of a model *at a point in time*.

### 1.3 Statistical power

A solo researcher will gather small samples. Consequences built into the
platform:

- No interval is computed below n = 8. A bootstrap from four points produces a
  confident-looking range that means nothing.
- n < 20 is labelled exploratory in the payload and in the report.
- **No p-values.** At these sample sizes a significance test would invite exactly
  the overclaiming the project is built to avoid.
- Observations are **clustered** — several ratings of one response, or several
  answers from one participant, are not independent. The platform detects this
  and the warning travels with the numbers, but it does not model the clustering
  (no mixed-effects model). The effective sample size is closer to the number of
  distinct units than to the row count.

Nothing here supports a claim like "T2 improves comprehension by 14%".

### 1.4 Participants are self-selected

Links are shared by the researcher, so participants are not a random sample of
any population. Prior-knowledge self-report is subjective and unverified.
Results describe the people who took the study.

### 1.5 The checklist coverage metric is lexical

`concept_coverage` uses keyword overlap, so a **correct paraphrase registers as
a miss**. It is a prompt for human review, not a correctness measure. The payload
says so and the UI repeats it.

### 1.6 Readability indices measure the wrong thing

Flesch-Kincaid and relatives were fitted to surface features and are not
validated comprehension measures; optimising them directly produces choppy,
less coherent text. They are reported because the brief asks for them, with a
standing caveat attached to the payload. **The platform never ranks a condition
by readability**, and neither should you.

### 1.7 Concept dependency graphs are hypotheses

Validated graphs are normally expert-authored. An LLM-inferred graph is a set of
claims about conceptual dependency. `is_hypothesis` is hardcoded `True`, the UI
labels every render, and low-confidence edges are drawn dashed.

The *sequencing violation count* derived from a graph is deterministic **given
that graph** — but it inherits the graph's uncertainty. "Three prerequisites are
introduced late" is a fact about the text relative to a hypothesis, not relative
to ground truth.

### 1.8 Fidelity verdicts are provisional

A `clean` verdict means **no problem was detected**, never *verified accurate*.
The deterministic layer catches numeric drift, hedge loss, length collapse and
boundary violations — real, checkable things. The LLM reviewer catches semantic
drift unreliably: it will miss some altered claims and flag some non-issues.
Every payload carries `provisional: true`.

Specifically **not** checked: whether either version is factually correct about
the world. Both could be wrong in the same way and the audit would report clean.

### 1.9 Treatment boundaries are enforced imperfectly

The boundary checks are heuristic. Counting added headings catches a vocabulary
treatment that restructured the document; it does not catch one that subtly
reordered two clauses. A variant that passes the boundary check is *probably* a
clean single-treatment condition, not certainly one.

### 1.10 Demo fixtures illustrate the hypothesis

The demo styles were hand-written by the project authors to produce the
contrast the research is about. That makes demo mode useful for seeing how the
screens behave, and makes it **circular as evidence**. Every such row is flagged
`SYNTHETIC` for life and excluded from results dashboards by default.

### 1.11 Source 5 was not retrieved

The Reddit thread the brief asks us to analyse
(`r/ClaudeAI/comments/1vzzbjj`) **could not be fetched** — reddit.com refuses
automated retrieval from this environment. We did not substitute a paraphrase
from memory and do not claim to have read it.

The complaint categories it was meant to supply are independently attested in
the Elixir Forum thread, which we did read in full
(`RESEARCH_FOUNDATIONS.md` §1.1). **To close this gap properly, a researcher
should open the thread manually and add notes to `RESEARCH_FOUNDATIONS.md` §1.5.**

### 1.12 Sources 2 and 4 are not independent

Both report the same unverified statement by one named Anthropic engineer,
relayed through secondary and partly translated outlets. We could not locate a
primary Anthropic publication. Counting them as two pieces of evidence would be
double-counting; `RESEARCH_FOUNDATIONS.md` §1.4 records the chain of custody.

### 1.13 Item ordering is partly fixed, for a reason

Free-text items are always presented after multiple-choice items, because
writing an explanation is itself a learning intervention (the self-explanation
effect) and would change later answers. This is a deliberate confound trade:
format order is not randomised, so a format-order effect cannot be separated
from a format effect. Order within each block is randomised and recorded.

### 1.14 The injection guard is a deviation from a true default condition

A one-sentence prompt-injection guard is appended to the system prompt in
**every** condition, including Condition A, which is therefore not literally
empty. It is applied identically across conditions and recorded on every
response. It is a security control we are not willing to drop, but a purist
"default model behaviour" measurement would not have it.

---

## 2. Technical limitations

### 2.1 Prompt injection is mitigated, not solved

Nonce-suffixed delimiters, a guard instruction, neutralised closing tags and
length limits reduce risk substantially. They do not eliminate it. A
sufficiently clever payload in an imported explanation may still influence a
judge or a transformation. Treat imported content from untrusted sources with
corresponding suspicion.

### 2.2 Authentication is a single shared token

Not per-user accounts, no roles, no audit trail of who did what. Appropriate for
a solo researcher or a small trusted team; not appropriate for an organisation.
With no token configured the API refuses non-local requests rather than running
open, but that is a blunt instrument.

### 2.3 No rate limiting on participant endpoints

A study token is unguessable, but once known nothing throttles requests to it.
Repeat exposure and resubmission are blocked, and arms can be capped — but a
determined actor could enumerate participant codes or submit noise. Acceptable
behind a shared link to known participants; not acceptable for public
recruitment.

### 2.4 The worker is single-process by default

`claim_next` uses `FOR UPDATE SKIP LOCKED` on Postgres, so multiple workers are
safe, and `docker compose` runs the worker as its own service. But the in-process
default executes runs sequentially, so a large batch is slow. There is no
parallelism within a batch.

### 2.5 Jobs do not resume mid-run

A job interrupted mid-run leaves that run in `running` state; it is picked up by
the next retry as a failure and re-executed from the start. Work already billed
for that run is lost. Completed runs are never re-executed.

### 2.6 Cost figures are estimates

Computed from configured per-model prices and provider-reported token counts.
They ignore tier differences, prompt caching discounts, batch pricing and
negotiated rates. Cached responses are billed as zero, which is right for the
cache but means the figure is not "what you would have paid". Authoritative
billing lives in your provider dashboard.

Pre-flight estimates use fixed token assumptions and will be wrong in either
direction.

### 2.7 Pricing and capability data go stale

The seed catalogue was verified on 2026-10-22. Prices change, models retire.
`POST /api/models/refresh` reconciles *existence* against the provider's live
list but cannot fetch prices. A newly discovered model is added disabled with no
pricing, so its calls record `cost_usd = 0.0` until an operator fills it in.

### 2.8 The Markdown renderer is a subset

It handles ATX headings, paragraphs, fenced code, blockquotes, lists, tables,
rules, and inline code/bold/italic/links. Not supported: nested lists beyond one
level, reference links, footnotes, inline HTML (rendered as literal text by
design), task lists, or setext headings. Unusual model formatting may render
plainly. This is the price of not using `innerHTML`, and it is worth paying.

### 2.9 Delayed retention is not implemented

The schema supports reassessing a participant later (dimension H), but there is
no scheduling, no reminder mechanism and no second-session flow. The brief lists
this as extensible rather than required; it is genuinely absent.

### 2.10 Diagram specifications are not rendered

T5 can emit a fenced `diagram` block with `A -> B: label` edges. It is stored and
displayed as text. Nothing renders it as a picture.

### 2.11 Jargon detection is heuristic

Long nominalised words plus a phrase list derived from the documented reader
complaints. Not a curated domain glossary, so it will flag legitimate technical
terms and miss domain-specific jargon. Useful as a signal to look at a text, not
as a measure.

### 2.12 No experiment-level pairing in the analysis UI

`stats.paired_difference` exists and is tested, but the results screens report
independent-group summaries. For a properly paired analysis — same question
under two conditions — export the JSON and do it yourself. The pairing is
available in the data.

### 2.13 Single-language

Everything is English. The non-native-English-reader learner profile exists
because that group is repeatedly identified as worst affected, but the platform
cannot generate or assess explanations in another language.

---

## 3. Product limitations

- **One researcher's view.** No collaboration features, comments, or shared
  review queues.
- **No participant recruitment.** You share a link. No panel integration, no
  incentives, no screening beyond self-report.
- **No PDF export.** CSV, JSON and Markdown only; the brief marks PDF optional.
- **No scheduled or recurring runs.**
- **Library search is basic.** Substring match on question text. No full-text
  search across stored responses.
- **No soft delete.** Deleting an experiment cascades to its runs and responses.
- **Dashboard aggregates are computed on request.** Fine at research scale;
  it will not stay fast at tens of thousands of responses.

---

## 4. What would most improve the research quality

In order of expected value, not effort:

1. **Expert-reviewed concept dependency graphs** for the seed questions. This
   would turn the sequencing measure from "deterministic given a hypothesis"
   into a real measurement, and is the single biggest upgrade available.
2. **A larger participant pool.** Everything statistical is limited by n.
   n = 30 per arm would change what can be said.
3. **Domain-expert review of the factual checklists.** They are currently an
   author's first pass, recorded honestly as such.
4. **Human-vs-judge agreement measurement.** Once enough human data exists,
   check whether the judge correlates with comprehension at all. It may not —
   and that would be worth knowing before trusting it for triage.
5. **Mixed-effects modelling** with question and participant as random effects,
   replacing the clustering *warning* with clustering *handled*.
6. **Delayed retention.** Immediate comprehension and retention can diverge, and
   retention is what matters.
