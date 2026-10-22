# Research Foundations

Evidence synthesis underpinning ExplanationLab. Written 2026-10-22.

Every claim below carries an explicit **evidence level**. The platform's scoring
logic must not encode any claim above its level.

| Level | Meaning |
| ----- | ------- |
| **L1 — Documented fact** | Stated in primary/official documentation or directly observable in an API. |
| **L2 — Academic finding** | Supported by peer-reviewed research, with known scope limits. |
| **L3 — Anecdote** | User reports, forum/community threads, press reporting of a single source. |
| **L4 — Engineering hypothesis** | Our own conjecture. Requires an ExplanationLab experiment. |

We have **no access** to OpenAI's or Anthropic's training pipelines, reward
models, or internal evaluations. Nothing here should be read as inside knowledge.

---

## 1. Source review

### 1.1 Elixir Forum — "I can't understand Claude's output anymore" (L3)

Thread: <https://elixirforum.com/t/i-cant-understand-claudes-output-anymore-is-it-just-me/76423>
Fetched 2026-10-22.

Recurring, concrete complaints — these are the phenomena worth operationalising:

| Reported phenomenon | Representative wording | Maps to treatment |
| ------------------- | ---------------------- | ----------------- |
| Cognitive density | text "so loaded, and complex, and full of indirection and propositions"; "Brain CPU" pegged | T1, T5 |
| Indirection | "verboseness, unnecessary fluff, and indirection" | T1 |
| Self-important register | "talks like it's delivering a TED talk about its own pull request"; "a load-bearing assumption"; "three numbered revelations" | T1 |
| Jargon burden on non-native readers | "pretentious jargon" singled out as especially tiring | T1, T6 |
| Vague generic nouns | undefined shorthand such as "arms", "legs", "frames" | T1 (ambiguous-reference resolution) |
| Unreadable prose at length | "borderline unreadable"; long contexts produce "spagetti (with sausages)" | T5 |

Community workarounds observed (each is an existence proof that *instruction-level*
intervention changes output; none is an effectiveness measurement):

- **caveman** — terseness skill, reported ~65% token reduction.
- **unslop** — "cut AI tells from any writing".
- **"I have ADHD" skill / "Attention Span" output styles** — plain-language modes.
- **ASD-STE100 Simplified Technical English** — a controlled-language standard,
  reported as working with "moderate success". This is the closest community
  analogue to our T1 treatment and is a genuinely interesting comparator.
- **Buzzword/devspeak bans** — lexical blocklists.
- One participant reports the **code** is not worse, possibly better — i.e. the
  complaint is about explanatory prose, not capability.

Unsubstantiated causal claims also appear in the thread ("model collapse",
"watermarks"). We record them as **L3 rumour** and do not act on them.

### 1.2 The Decoder — Anthropic engineer on writing quality (L3)

<https://the-decoder.com/anthropic-engineer-explains-why-claudes-writing-got-worse-although-the-model-got-smarter/>

- Attributed to **Jackson Kernion** (works on Claude fine-tuning at Anthropic),
  quoting posts on X. The article does not reproduce the full posts.
- Quoted fragments: output "adapted to LLM psychology"; "overly-dense info dumps";
  "It's a hard problem to solve, and we'll continue to make improvements"; he has
  not been "as happy about a model's writing since Opus 4.6".
- Reported mechanism: heavy optimisation for math/code; reward signals that favour
  *machine* comprehension over *human* comprehension.
- **The journalist's own framing** — that the model "learned to write for AI
  models, not for people", and the working-memory explanation — is explicitly
  interpretation, not quotation.

**Status: L3.** A named engineer's informal social-media remarks relayed by a
trade outlet. It is a *motivating* observation, not a demonstrated mechanism. We
could not locate an official Anthropic publication making this claim.

### 1.3 Ruben Hassid / Substack — "Stop prompting Claude" (L3 + L1)

<https://ruben.substack.com/p/stop-prompting-claude>

Argument: one-off prompts underperform because the model lacks persistent context
(tone, audience, standing rules). Remedy: keep that context in durable files —
"The files are the prompt. Forever." Recommends an about-me file, a separate
anti-AI-writing-style file, a company/background file, standing behavioural rules
("ask questions before executing any task"), repeated tasks promoted to Skills,
and a style **audit pass** run against the style file before delivery.

- **L1 component:** persistent-instruction mechanisms (Projects, Skills, global
  instructions) exist and are documented product features.
- **L3 component:** that they improve *explanation comprehensibility* is the
  author's experience, measured by nothing.
- **Design import:** the self-audit pass directly motivates our pipeline **Stage D**
  (fidelity verification) and argues that prompt artefacts should be
  **versioned, persisted objects** — which is why prompt templates are
  first-class versioned rows in our schema, not string literals.

Caveat noted in the brief, and confirmed on reading: this article is about
workflow and context management generally, not specifically about poor
explanation quality.

### 1.4 Tech Insider (L3, substantially derivative)

<https://tech-insider.org/anthropic-engineer-claude-writing-quality-worse-2026/>

Covers the same Kernion claim. Chain-of-custody matters here:

- Kernion's statements reach this article via **Sina Finance, Ground News and
  "Mo Explains"** — secondary, partly translated, syndicated. The article itself
  concedes there is no Anthropic blog post or verbatim English transcript.
- It cites The Decoder only for a *different* September 2025 event (confirmed
  Claude Code bugs affecting Sonnet 4 / Haiku 3.5), **not** for the writing claim.
- A claimed "95% reduction in em dashes" is **Anthropic's own** figure; the
  article labels an Arena analysis "independent confirmation" but that analysis
  reaches it through Ground News and repeats the same 95% figure — plausibly a
  restatement rather than an independent measurement.
- A "47% code-quality decline" comes from one evaluator's proprietary tool.

**Conclusion required by the brief:** Sources 1.2 and 1.4 are **not independent
evidence**. They are two reports of one unverified primary statement. Counting
them twice would be double-counting. The article's own FAQ is more candid about
this than its headline.

One substantive and checkable point: there is **no widely adopted prose/explanation
benchmark comparable to SWE-bench**. That absence is ExplanationLab's reason to exist.

### 1.5 Reddit r/ClaudeAI (not retrieved)

<https://www.reddit.com/r/ClaudeAI/comments/1vzzbjj/claude_is_significant_worse_at_communicating_than/>

**Could not be fetched** — reddit.com refuses automated retrieval from this
environment. We did not substitute a paraphrase from memory, and we do not claim
to have read it.

The complaint categories the brief asks us to analyse (jargon, overcomplication,
unnatural phrasing, misused technical vocabulary, overconfidence, "explain
simply" failing to produce understanding, patronising oversimplification,
hard-to-follow code explanations) are nonetheless **independently attested** in
§1.1, which we did read in full. Two of them matter enough to become first-class
platform concepts because they are *failure modes of the fix itself*:

- **"Simplify" that does not increase understanding** — motivates measuring
  comprehension, not perceived simplicity (§8.3 of the brief).
- **Patronising oversimplification** — motivates an explicit anti-patronising
  constraint in Condition C and in every treatment prompt, plus a participant
  rating dimension.

To close this gap properly a researcher should open the thread manually and add
notes here. Logged in `KNOWN_LIMITATIONS.md`.

---

## 2. Learning-science foundations (L2)

These are the mechanisms our treatments operationalise. Each is a *well-supported
finding with scope limits*, not a guarantee of transfer to LLM output.

**Cognitive Load Theory** (Sweller, 1988; Sweller, van Merrienboer & Paas, 1998/2019).
Working memory is severely limited; instructional design should minimise
extraneous load while preserving load intrinsic to the material. Supports T1 and
T5. **Scope limit:** "reduce load" is not "reduce content" — stripping intrinsic
content lowers load *and* learning. This is precisely why T1 is constrained to
preserve technical meaning and why Stage D checks for information loss.

**Expertise reversal effect** (Kalyuga et al., 2003). Scaffolding that helps
novices *harms* experts. This is the strongest theoretical reason the platform
must treat learner level as an experimental factor (T6, H4) rather than seeking a
single "best" explanation. It also predicts that an unconditionally applied
transformation set will show a *smaller* average effect than a profile-matched one.

**Worked-example effect** (Sweller & Cooper, 1985; Renkl, 2014). Studying worked
examples outperforms unguided problem solving for novices; the benefit decays
with expertise. Supports T4. **Scope limit:** established for procedural and
problem-solving domains; weaker evidence for conceptual prose.

**Self-explanation effect** (Chi et al., 1989, 1994). Learners who explain
material to themselves learn more. Relevant to our *assessment* design: asking a
participant to explain a mechanism in their own words is both a measurement and
an intervention — an order effect we must control (we therefore place free-text
mechanism questions after multiple-choice items and record item order).

**Prerequisite structure / knowledge spaces** (Doignon & Falmagne; Scheines et al.,
2005 on concept dependency). Learning is sensitive to the order in which
prerequisite concepts are introduced. Supports T2. **Scope limit:** validated
dependency graphs are normally *expert-authored*. An LLM-inferred graph is a
hypothesis, and the UI must label it as such.

**Coherence / signalling / segmenting principles** (Mayer's multimedia learning
work). Removing extraneous material, signalling structure, and segmenting content
improve learning. Supports T5. **Scope limit:** mostly established for multimedia;
most of our stimuli are text.

**Readability formulas measure the wrong thing** (Bruce & Rubin, 1988;
Davison & Kantor, 1982). Flesch-Kincaid and relatives were fitted to surface
features (word and sentence length) and are *not* validated measures of
comprehension; optimising them directly can produce choppy, less coherent text.
**This is a hard constraint on our metrics layer:** readability indices are
diagnostics only. The platform must never rank a condition by readability score,
and the UI labels them as surface diagnostics.

**Illusion of fluency** (Bjork & Bjork; Carpenter et al., 2013). Perceived ease of
learning dissociates from — and can be negatively correlated with — actual
retention. **This is the single most important methodological consequence in the
whole project:** perceived clarity (dimension D) and comprehension (A/B/C) must be
reported as separate measures and never averaged into one "quality" score.
A transformation that raises clarity ratings while lowering transfer scores is a
*finding*, and the platform must be able to express it.

**LLM-as-judge reliability** (Zheng et al., 2023 MT-Bench/Chatbot Arena; Wang et
al., 2023). LLM judges correlate usefully with human preference but exhibit
position bias, verbosity bias, and self-enhancement bias. Mitigations we
implement: randomised presentation order, blinding to model identity, a judge
model configurable independently of the generating model, and persistent labelling
of judge output as provisional opinion. **Scope limit:** these judges are
calibrated against *human preference*, which §8.3 of the brief correctly refuses
to treat as comprehension.

**Faithfulness in text transformation** (summarisation-factuality literature,
e.g. Maynez et al., 2020; Kryscinski et al., 2020). Abstractive rewriting
reliably introduces unsupported content. Base rates are non-trivial. Therefore a
fidelity check is **mandatory** on every transformation, not optional, and
"no warnings" must never be rendered as "verified correct".

---

## 3. Provider-documented facts relevant to the design (L1)

Verified against official documentation on 2026-10-22.

**Anthropic** (`claude-opus-5-5` $4/$20 per MTok, `claude-sonnet-5-5` $2/$10,
`claude-haiku-5-5` $0.10/$0.50):

- On current models (Opus 5.5, Sonnet 5.5, Haiku 5.5) **`temperature` is rejected
  with HTTP 400**, not merely ignored. Thinking cannot be disabled on Opus 5.5.
  Generation depth is controlled by `output_config.effort`, whose default is
  `medium` on Opus 5.5.
- Forced tool use (`tool_choice: any|tool`) returns 400 on current models;
  structured extraction uses `output_config.format` with a JSON schema.

**OpenAI** (`gpt-6-astra` $10/$50, `gpt-6.1-sol` $2/$10, `gpt-6-luna` $0.10/$0.50):

- Current models are served through the **Responses API**; structured outputs nest
  as `text.format.{type,name,strict,schema}`.

**Consequence for experimental control — this is a genuine methodological finding,
not a bug.** The brief asks for "comparable, documented generation conditions".
On today's frontier models that is **partly unachievable**: sampling temperature,
the classical lever for holding generation conditions constant, does not exist on
either provider's current flagship line. ExplanationLab therefore:

1. stores a per-model **capability record** (`supports_temperature`,
   `supports_effort`, `supports_max_output_tokens`);
2. **omits** unsupported parameters rather than silently substituting a model;
3. records every omission as a `control_limitation` string on the run, surfaced in
   the comparison UI and in every exported report.

Pretending the two configurations are identical would be the actual error.

---

## 4. Hypotheses and what would falsify them

The brief's H1–H5, restated as testable predictions with named failure conditions.
All are **L4**.

| # | Hypothesis | Prediction | Falsified if |
| - | ---------- | ---------- | ------------ |
| **H1** | Default behavioural alignment, not capability, drives the baseline gap | Condition C narrows the cross-model comprehension gap vs Condition A | the gap is unchanged or widens under C |
| **H2** | Prerequisite-aware sequencing is a primary mechanism | T2 alone improves comprehension without vocabulary simplification | T2 alone shows no effect while T1 alone does |
| **H3** | Presentation effects explain part of the perceived difference | T5 raises *perceived clarity* more than *comprehension* | T5 moves comprehension as much as clarity |
| **H4** | Audience adaptation matters | profile-matched explanations beat mismatched ones; effect reverses by level (expertise reversal) | matched and mismatched perform equally across levels |
| **H5** | Residual model-specific capability persists | a gap survives identical prompts, treatments, profiles and formatting | gaps vanish once conditions are equalised |

**Pre-registered confound we expect:** H3 and the illusion-of-fluency literature
jointly predict that *perceived clarity will overstate comprehension gains*. If
our dashboard ever shows a single blended "explanation quality" number, that
prediction becomes untestable. It does not.

---

## 5. What this platform deliberately does *not* claim

- That ChatGPT or Claude is the better teacher. Principle 7. No scoring path
  contains a model-identity term; the judge is blinded and answer order randomised.
- That an LLM judge measures understanding. It measures a judge model's opinion.
- That LLM-inferred prerequisite edges are ground truth. They are hypotheses, and
  the graph UI says so on every render.
- That demo-mode fixtures are findings. Synthetic provenance is stored on the row,
  propagates into every aggregate, and is rendered as a warning wherever it appears.

---

## 6. References

- Bjork, R. A., & Bjork, E. L. Desirable difficulties and the illusion of learning.
- Bruce, B., & Rubin, A. (1988). *Readability formulas: Matching tool and task.*
- Carpenter, S. K., et al. (2013). Why lectures can be deceptive: fluency and
  judgments of learning.
- Chi, M. T. H., et al. (1989, 1994). Self-explanations; eliciting self-explanations.
- Davison, A., & Kantor, R. N. (1982). On the failure of readability formulas.
- Doignon, J.-P., & Falmagne, J.-C. *Knowledge Spaces.*
- Kalyuga, S., Ayres, P., Chandler, P., & Sweller, J. (2003). The expertise
  reversal effect. *Educational Psychologist, 38*(1).
- Kryscinski, W., et al. (2020). Evaluating the factual consistency of abstractive
  summarization.
- Mayer, R. E. *Multimedia Learning* (coherence, signalling, segmenting principles).
- Maynez, J., et al. (2020). On faithfulness and factuality in abstractive
  summarization. *ACL.*
- Renkl, A. (2014). Toward an instructionally oriented theory of example-based
  learning. *Cognitive Science.*
- Scheines, R., et al. (2005). Learning concept dependency structure.
- Sweller, J. (1988). Cognitive load during problem solving. *Cognitive Science.*
- Sweller, J., & Cooper, G. A. (1985). The use of worked examples.
- Sweller, J., van Merrienboer, J., & Paas, F. (1998; rev. 2019). Cognitive
  architecture and instructional design. *Educational Psychology Review.*
- Wang, P., et al. (2023). Large language models are not fair evaluators.
- Zheng, L., et al. (2023). Judging LLM-as-a-judge with MT-Bench and Chatbot Arena.
- Anthropic API documentation (models, pricing, structured outputs) — 2026-10-22.
- OpenAI API documentation (models, pricing, structured outputs) — 2026-10-22.
- Sources §1.1–§1.5 above, with retrieval status noted per source.
