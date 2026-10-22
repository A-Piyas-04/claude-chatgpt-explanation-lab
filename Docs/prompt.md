# MASTER IMPLEMENTATION PROMPT
# ExplanationLab — AI Explanation Quality Research Platform

## 0. Your Role and Operating Instructions

You are acting as a team consisting of:

- Senior Full-Stack Software Engineer
- AI/LLM Systems Architect
- Prompt Engineering and LLM Evaluation Researcher
- Learning Science and Instructional Design Researcher
- Experimental Design and Data Analysis Specialist
- Senior Product and UI/UX Designer

Your responsibility is to **research, architect, implement, test, and document a working MVP of ExplanationLab**, an experimental platform for studying and improving the human comprehensibility of AI-generated explanations.

This is a software implementation task, not a request to merely propose architecture or write a product requirements document.

Produce the actual working application with properly organized source code, integrations, database, usable interface, tests, configuration, and documentation.

Make reasonable engineering decisions independently. Do not stop at a plan or ask unnecessary clarifying questions.

Use current official SDK documentation and verify that selected APIs and model identifiers are available before implementation.

---

# 1. Product Background

## 1.1 The problem

The project originates from a recurring observation about the conversational interfaces of ChatGPT and Claude.

Both systems can provide technically knowledgeable, useful, and accurate responses.

However, their explanations sometimes differ dramatically in how understandable they are to human readers.

A user may find that ChatGPT:

- Explains concepts in a natural, easily understandable way.
- Uses clear, straightforward sentences.
- Introduces concepts in an appropriate sequence.
- Recognizes when prerequisite knowledge must be introduced.
- Uses concrete scenarios and real-world examples.
- Explains not only what something is, but how and why it works.
- Organizes information into readable sections.
- Avoids unnecessarily complex vocabulary and dense prose.
- Teaches as if genuinely trying to help a human understand.

Meanwhile, the same user may experience Claude responses that:

- Are technically sophisticated but difficult to follow.
- Contain overly dense paragraphs.
- Introduce too many unfamiliar ideas simultaneously.
- Use unusual terminology or unnecessary jargon.
- Compress several reasoning steps into one sentence.
- Assume prerequisite knowledge.
- Contain vague references, abstractions, or indirect wording.
- Become excessively simplified or patronizing when instructed to "explain simply."
- Use formatting that does not reveal the underlying conceptual structure.
- Remain difficult to understand despite explicit tutoring instructions.

These are user observations, not established universal facts about either model.

Our goal is to investigate these phenomena scientifically and identify techniques that measurably improve comprehension.

## 1.2 Critical distinction

**Explanation quality is NOT the same as factual correctness, reasoning intelligence, writing elegance, answer length, or visual attractiveness.**

We are studying how effectively an explanation transfers knowledge from an AI system to a human reader.

An excellent explanation should allow the reader to:

1. Understand the individual statements.
2. Follow the logical progression.
3. Build a mental model of the concept.
4. Understand the underlying mechanisms.
5. Connect new knowledge to familiar experiences.
6. Remember important principles.
7. Apply the knowledge to an unfamiliar situation.
8. Avoid developing incorrect misconceptions.

The fundamental research question is:

**Can we improve a model's explanatory effectiveness through an explicit, model-independent pedagogical transformation process, without retraining the underlying model?**

We also want to discover which specific mechanisms contribute most strongly to any improvements.

---

# 2. Ultimate Product Roadmap

The project has four stages.

### Stage 1 — ExplanationLab Research Platform

Build a full-stack research application to compare LLM explanations, experiment with pedagogical transformations, and measure explanation effectiveness.

This is the CURRENT implementation target.

### Stage 2 — Claude Skill

Use successful techniques discovered through ExplanationLab to build an installable Claude Skill or compatible instruction-based integration.

Its purpose is to make Claude communicate more understandably without sacrificing technical sophistication or accuracy.

### Stage 3 — Improved Explanation Engine

If instruction-based approaches prove insufficient, implement a reusable explanation-processing engine that can independently analyze, restructure, and improve LLM responses.

### Stage 4 — Universal Browser Extension

Eventually create an extension or compatible integration capable of improving explanations across multiple AI chat interfaces.

Do NOT implement Stages 2–4 now.

However, design the MVP with clear reusable modules, so useful transformation algorithms and evaluator components can later be extracted into those products.

---

# 3. Required Preliminary Research

Before finalizing the implementation, inspect the following five sources.

## Source 1 — Elixir Forum

https://elixirforum.com/t/i-cant-understand-claudes-output-anymore-is-it-just-me/76423

Investigate complaints about:

- Cognitive density.
- Unnatural sentence structures.
- Indirect wording.
- Excessively compressed explanations.
- Unnecessary terminology.
- User frustration despite technical competence.
- Difficulties experienced by non-native English speakers.
- Existing community-created rewriting skills and workarounds.

## Source 2 — The Decoder

https://the-decoder.com/anthropic-engineer-explains-why-claudes-writing-got-worse-although-the-model-got-smarter/

Investigate reported explanations involving:

- Reinforcement-learning reward design.
- Optimization for coding and mathematical reasoning.
- Human-oriented versus machine-oriented communication.
- Writing-style shifts during model development.
- Trade-offs between technical capability and comprehensibility.

Where possible, trace important claims to the primary statements and official documentation.

Do not assume that a reported causal mechanism has been independently proven.

## Source 3 — Ruben Hassid / Substack

https://ruben.substack.com/p/stop-prompting-claude

Investigate the role of:

- Persistent instructions.
- Context and audience specification.
- Reusable workflows.
- Claude Projects, Skills, or similar mechanisms.
- Writing-quality audits.
- Limitations of short generic prompts.
- Approaches that avoid manually repeating long instructions.

Note: this article discusses broader Claude workflows and context management, not simply poor explanation quality.

## Source 4 — Tech Insider

https://tech-insider.org/anthropic-engineer-claude-writing-quality-worse-2026/

Investigate:

- Writing-style degradation claims.
- Training reward trade-offs.
- Communication optimized for AI versus human readers.
- Community observations.
- Potential corrective strategies.
- Any relevant discussion of evaluation benchmarks.

Check whether this article and Source 2 rely on the same underlying statements.

**Do not count repeated reporting of one source as independent evidence.**

## Source 5 — Reddit Community Discussion

https://www.reddit.com/r/ClaudeAI/comments/1vzzbjj/claude_is_significant_worse_at_communicating_than/

Analyze:

- Excessive jargon.
- Overcomplicated communication.
- Unnatural phrasing.
- Misuse of technical vocabulary.
- Overconfidence in explanations.
- Users requesting simpler answers without achieving better understanding.
- Oversimplification that becomes patronizing.
- Difficulties understanding AI-generated code explanations.

Treat personal experiences as qualitative research leads, not scientific evidence that one model is universally superior.

## Additional research

Supplement these sources with credible material on:

- OpenAI Model Spec and explanation-related behavioral guidance.
- Anthropic's public prompting and system behavior guidance.
- Human preference optimization and post-training.
- Cognitive Load Theory.
- Instructional scaffolding.
- Worked-example effects.
- Concept dependency graphs.
- Prerequisite-aware learning.
- Mental model formation.
- Self-explanation.
- Adaptive tutoring.
- Instructional sequencing.
- Readability versus comprehension.
- Human-centered LLM evaluation.
- Knowledge transfer and misconception detection.
- Factual consistency in text transformations.

Use official documentation, academic research, and primary sources when available.

Create a concise research synthesis in `docs/RESEARCH_FOUNDATIONS.md`.

For every major proposed mechanism, distinguish:

1. Publicly documented facts.
2. Findings supported by academic research.
3. Anecdotal user reports.
4. Engineering hypotheses requiring experiments.

Do not claim access to proprietary ChatGPT or Claude training systems.

---

# 4. What We Need to Discover

We have five initial hypotheses.

### H1 — Default Behavioral Alignment

ChatGPT may perform better at explanation tasks because its default response behavior favors readable, understandable communication.

Prediction: Strong instructions may reduce the explanation-quality gap.

### H2 — Pedagogical Sequencing

One model may introduce concepts in an order that is more conducive to understanding.

Prediction: Reorganizing information based on prerequisite concepts improves comprehension even without extensively simplifying the vocabulary.

### H3 — Presentation Effects

Readable formatting, short sections, diagrams, and visual structure may improve perceived or actual comprehension.

Prediction: Standardizing presentation reduces some measurable differences between outputs.

### H4 — Audience Adaptation

Explanation quality may depend on whether the response matches a learner's existing knowledge.

Prediction: Explanations tailored to prior knowledge improve learning outcomes.

### H5 — Model-Specific Capability

Differences may persist even after controlling for prompts, transformations, learner profiles, and formatting.

Prediction: Some explanation capabilities may remain difficult to reproduce through external processing alone.

These hypotheses are NOT conclusions.

The application must allow us to test them.

---

# 5. Core Application Concept

**Product name: ExplanationLab**

A professional, experiment-driven AI explanation research platform.

A researcher enters a question, selects models and settings, and generates comparable explanations.

The application then supports different controlled experimental conditions, including prompt changes and explicit pedagogical transformations.

Human evaluators can read anonymized explanations, complete comprehension questions, and rate communication quality.

The platform analyzes the resulting data.

The system should answer questions such as:

- Which model gives a more understandable baseline explanation?
- Which prompt design produces the strongest improvement?
- Does simplifying vocabulary improve understanding?
- Is sequencing more important than formatting?
- Do concrete examples outperform abstract descriptions?
- Can Claude explanations be improved without changing their technical meaning?
- Which transformations introduce misconceptions?
- Which techniques work best for beginners versus advanced learners?
- How much additional model cost and latency does each technique require?

---

# 6. Five Required Experiments

All five experiments must be supported within ExplanationLab.

The application must clearly label experimental conditions and distinguish automatic analysis from real human evaluation.

## Experiment 1 — Baseline Model Comparison

### Objective

Compare the default explanation styles of ChatGPT and Claude.

### Input

- One or multiple research questions.
- Subject area.
- Audience profile.
- Selected OpenAI model.
- Selected Anthropic model.
- Model generation settings.

### Procedure

1. Submit an identical user question to both models.
2. Apply comparable, documented generation conditions.
3. Avoid adding a detailed tutor prompt in the baseline condition.
4. Record all controllable system and developer instructions.
5. Generate the responses independently.
6. Store the raw model outputs.
7. Capture generation metadata.
8. Display the results side by side.
9. Permit manual annotation of explanation characteristics.
10. Support blinded evaluation using a common rendering interface.

### Important controls

Do not assume OpenAI API responses and ChatGPT's consumer interface are identical.

Similarly, do not assume the Anthropic API reproduces every aspect of Claude's consumer interface.

Add an optional manual-import mode to paste actual responses from ChatGPT and Claude web chats.

Store provenance:

- Provider.
- Model.
- Exact model identifier.
- API-generated or manually imported.
- Timestamp.
- Relevant generation settings.
- Prompt configuration.

### Deliverable

A baseline comparison report that does not automatically assume ChatGPT is superior.

---

## Experiment 2 — Prompt Intervention

### Objective

Determine whether better prompting produces significantly more understandable explanations.

Implement three required conditions:

**Condition A: Default**

Original model behavior without special pedagogical instructions.

**Condition B: Generic Tutor Prompt**

A conventional instruction such as:

"Act as a helpful tutor. Explain clearly, step by step, using simple language and practical examples."

**Condition C: Structured Pedagogical Prompt**

A detailed instruction defining a teaching process rather than merely requesting clear language.

It should require the model to:

1. Infer the likely learner level from the supplied profile.
2. Identify prerequisites.
3. Establish the problem or motivation.
4. Introduce concepts in a logical order.
5. Explain mechanisms, not only definitions.
6. Ground abstractions in practical examples.
7. Explain jargon when introduced.
8. Preserve technical accuracy.
9. Avoid patronizing oversimplification.
10. Avoid unnecessary repetition and verbosity.

Allow researchers to edit and version these prompts.

### Application features

- Prompt template management.
- Three-condition comparison.
- Identical-question batch runs.
- Version history.
- Prompt parameter inspection.
- Results storage.
- Reproducible experiment runs.

### Deliverable

Evidence about whether prompt instructions alone are sufficient to improve explanations.

---

## Experiment 3 — Mechanism Isolation / Ablation

### Objective

Identify which specific explanation-improvement techniques are effective.

Implement these transformation treatments independently.

**T1: Vocabulary and Sentence Clarification**

- Replace unnecessary jargon.
- Explain essential technical terminology.
- Shorten unnecessarily complicated sentences.
- Resolve ambiguous references.
- Reduce excessive indirect wording.
- Preserve original technical meaning.

**T2: Prerequisite-Aware Concept Sequencing**

- Identify major concepts.
- Identify concepts required to understand other concepts.
- Construct a concept dependency graph.
- Determine a reasonable teaching order.
- Reorganize the explanation accordingly.
- Explain necessary prerequisites before dependent ideas.

**T3: Mechanism and Causal Explanation**

- Explain what happens.
- Explain why it happens.
- Explain how the components interact.
- Reveal missing intermediate steps.
- Distinguish causes, effects, conditions, and exceptions.

**T4: Concrete Examples and Analogies**

- Introduce a realistic example when useful.
- Explain how the example maps to the technical concept.
- Identify where an analogy stops being accurate.
- Avoid unrelated decorative examples.
- Avoid childish or patronizing analogies for adult learners.

**T5: Structural and Visual Presentation**

- Improve headings and hierarchy.
- Use short paragraphs.
- Use ordered steps for procedures.
- Use comparison tables where genuinely useful.
- Generate simple diagrams for mechanisms and flows.
- Avoid formatting for its own sake.

**T6: Audience Adaptation**

- Beginner, intermediate, and advanced learner profiles.
- Control assumed prior knowledge.
- Adjust explanations without changing the underlying facts.
- Make prerequisite handling dependent on the learner profile.

### Required comparison conditions

Allow selection of:

- Original answer.
- Each individual treatment.
- Combined treatments.
- Custom researcher-defined combinations.

Do not force all treatments on every explanation.

A simple topic might not need an analogy, diagram, or prerequisite graph.

### Implementation requirement

Design a transformation pipeline using modular strategies.

Each strategy should have:

- Unique identifier.
- Description.
- Versioned instruction template.
- Input schema.
- Output schema.
- Configurable parameters.
- Recorded provenance.
- Evaluation metadata.

The transformation system must permit independent execution and composition.

### Deliverable

An ablation report measuring which techniques work individually and together.

---

## Experiment 4 — Cross-Model Explanation Transformation

### Objective

Determine whether an external pedagogical processing system can substantially improve an answer generated by another LLM.

### Procedure

1. Generate or import a Claude explanation.
2. Preserve the original response.
3. Apply a selected explanation transformation.
4. Generate an improved explanation.
5. Compare the original with the transformed version.
6. Measure comprehensibility and factual fidelity.
7. Repeat across different questions and learner profiles.

### Critical research requirement

Avoid confusing the explanation engine's capability with the capability of the model performing the transformation.

Support configuration of the transformation model separately from the source model.

For example:

- Claude generates, Claude transforms.
- Claude generates, OpenAI transforms.
- OpenAI generates, Claude transforms.
- OpenAI generates, OpenAI transforms.

Allow the researcher to identify whether improvements arise from the transformation methodology, the transformation model, or their interaction.

### Preserve meaning

The transformed explanation must not:

- Silently change technical claims.
- Invent factual examples that contradict the original.
- Remove critical limitations.
- Introduce unjustified certainty.
- Change formulas or numerical values.
- Introduce false simplifications.

Provide a factual fidelity review that flags potentially altered, omitted, or newly introduced claims.

Automated factual checks may use an LLM judge, but must clearly be identified as provisional assessments, not proof of correctness.

### Deliverable

A cross-model transformation comparison report.

---

## Experiment 5 — Blind Human Comprehension Testing

### Objective

Evaluate whether explanations help real humans understand and apply concepts.

This experiment is essential.

**Do not simulate human comprehension using another LLM and report it as real learner evidence.**

### Evaluator workflow

1. Researcher creates a study.
2. Selects eligible answer variants.
3. Configures learner audience criteria.
4. Defines comprehension questions.
5. Publishes a shareable participant link.
6. Participant enters the study.
7. Participant optionally completes a short prior-knowledge assessment.
8. System assigns an eligible explanation condition.
9. Participant reads the explanation without knowing its source.
10. Participant completes a comprehension assessment.
11. System stores scores, reading duration, and feedback.
12. Researcher reviews aggregate results.

### Blind testing

Participants must not see model identities or treatment names while evaluating.

Use randomized answer allocation.

Support seeded randomization for reproducibility.

Where practical, balance condition assignment counts.

Avoid giving the same learner multiple explanations about the same concept before completing the comprehension assessment.

### Required evaluation dimensions

**A. Immediate comprehension**

Can the participant correctly explain or identify the concept?

**B. Mechanistic understanding**

Does the participant understand how and why the process works?

**C. Transfer**

Can the participant apply the explanation to a new situation?

**D. Perceived clarity**

How easy was the explanation to follow?

**E. Cognitive effort**

How mentally demanding was the explanation?

**F. Misconception detection**

Did the participant develop an incorrect understanding?

**G. Time**

How much time was required to read and answer?

**H. Optional delayed retention**

Support later reassessment as an extensible feature, but do not require automated reminders for the MVP.

### Question formats

Include:

- Multiple-choice.
- Short answer.
- Scenario application.

Provide manual grading for short answers and optional AI-assisted grading.

Store the grading rubric and version.

Automated grading must not silently replace human judgments in final research conclusions.

### Participant protection

- Use anonymous participant IDs.
- Avoid collecting unnecessary personal information.
- Provide a short study consent notice.
- Permit participants to withdraw.
- Do not publicly expose individual results.
- Store assessment answers securely.

### Deliverable

A human comprehension study report comparing the assigned conditions.

---

# 7. Shared Experimental Controls

Every experiment must record enough information to reproduce its conditions.

Required fields include:

- Experiment type.
- Research question.
- Topic and domain.
- Learner profile.
- Source provider.
- Source model identifier.
- Source response.
- Prompt template and version.
- Transformation strategies and versions.
- Transformation model.
- Generation settings where supported.
- Randomization seed where relevant.
- Timestamp.
- Token usage where available.
- Estimated API cost where pricing is configured.
- Latency.
- Evaluation results.
- Factual fidelity warnings.
- Errors and retries.

Do not invent unavailable metadata.

Different providers may not support equivalent controls. Record these limitations instead of pretending the configurations are identical.

Support multiple runs of the same condition to measure response variability.

Use matched question sets when comparing conditions.

Avoid treating individual answer ratings as independent samples if the same question, learner, or model response appears repeatedly.

---

# 8. Evaluation Framework

Create a clear distinction between the following three measurement categories.

## 8.1 Automated Text-Level Diagnostics

Implement explainable metrics, where feasible, such as:

- Word count.
- Sentence count.
- Average sentence length.
- Paragraph length.
- Readability indicators.
- Repetition.
- Identifiable jargon.
- Terminology introduction order.
- Concept coverage.
- Explanation step coverage.
- Potentially unresolved references.
- Structural hierarchy.

These metrics are diagnostic signals, not direct measures of understanding.

Do not conclude that shorter sentences automatically mean better explanations.

## 8.2 AI-Assisted Evaluation

Support a configurable judge model.

Evaluate:

- Clarity.
- Logical progression.
- Prerequisite handling.
- Mechanism explanation.
- Example quality.
- Audience suitability.
- Unnecessary complexity.
- Potential information loss.
- Factual fidelity.

Require structured evaluation output containing:

- Metric.
- Score.
- Explanation of score.
- Evidence from the response.
- Confidence or uncertainty where meaningful.
- Improvement suggestions.

Use explicit scoring rubrics.

Avoid relying on one AI judge as the definitive source of truth.

Where feasible, blind the judge to model identity and randomize answer order.

## 8.3 Human Learning Evaluation

Treat actual learner assessments as the main evidence of comprehension.

Provide:

- Per-condition comprehension results.
- Average assessment scores.
- Transfer-question performance.
- Reading time.
- Participant clarity ratings.
- Cognitive-effort ratings.
- Misconception frequency.
- Participant count.

For sufficiently sized datasets, support uncertainty estimates, such as confidence intervals or bootstrap intervals, and paired analyses where experimental design supports them.

Clearly identify exploratory studies and small sample sizes.

**Never generate fictional research findings to populate the real results dashboard.**

Demo data, if provided, must be prominently labeled as synthetic.

---

# 9. Recommended Technical Architecture

Use a modular full-stack architecture.

Preferred technologies:

### Frontend

- Next.js with App Router.
- React.
- TypeScript.
- Tailwind CSS.
- shadcn/ui or similarly accessible component primitives.
- TanStack Query when beneficial.
- React Flow for interactive concept dependency graphs.
- Recharts or a comparable charting library.

### Backend

- Python.
- FastAPI.
- Pydantic for request and response validation.
- Official OpenAI SDK.
- Official Anthropic SDK.
- Async HTTP operations where appropriate.

### Database

Prefer PostgreSQL with SQLAlchemy and Alembic migrations.

For easy local setup, a database started through Docker Compose is acceptable.

### Application execution

- Docker Compose for repeatable development.
- Environment-based configuration.
- Separate frontend and backend services.
- A worker or background-job mechanism for longer experiment batches.

Choose a minimal, reliable job system for the MVP. Do not introduce unnecessary distributed infrastructure.

### Architecture requirement

Organize into modules such as:

```text
explanationlab/
├── apps/
│   ├── web/
│   └── api/
├── packages/
│   └── shared-schemas/
├── docs/
├── experiments/
├── evaluation/
├── transformations/
├── tests/
├── docker-compose.yml
├── .env.example
└── README.md
```

Adjust the structure if a cleaner architecture is justified.

The important requirement is separation of responsibilities.

### Backend subsystems

1. Provider adapter layer.
2. Prompt template registry.
3. Experiment orchestration engine.
4. Pedagogical transformation engine.
5. Concept graph analyzer.
6. Automated metrics engine.
7. LLM judge adapter.
8. Human study management.
9. Statistical analysis and reporting.
10. Database persistence.
11. Usage, cost, and error tracking.

Do not hardcode the entire experimental workflow inside one API endpoint.

---

# 10. Provider Integration

Support OpenAI and Anthropic.

### API configuration

Use server-side environment variables or a secure configuration mechanism.

Never expose API keys in client-side bundles.

Do not log secrets.

Do not store API keys in experiment records.

### Model configuration

Allow the researcher to select models from verified supported model IDs.

Avoid hardcoding obsolete model identifiers.

Provide:

- Source model selection.
- Transformation model selection.
- Judge model selection.
- Timeout configuration.
- Retry behavior.
- Token limit configuration.
- Provider availability indicators.

Show real errors instead of silently substituting an unrelated model.

### Cost controls

This is a research MVP and should not unintentionally generate expensive API bills.

Implement:

- Estimated run cost before batch execution where possible.
- Maximum batch size.
- Token usage tracking.
- Cost tracking.
- Explicit confirmation for unusually expensive batches.
- Caching of identical deterministic requests when appropriate.
- Clear indication when cached outputs are reused.
- Prevention of accidental duplicate submissions.

The MVP must work without purchasing premium AI tools beyond the model APIs selected by the operator.

---

# 11. Pedagogical Transformation Engine

This is the most important reusable subsystem.

Do not implement it as one giant prompt that says, "Rewrite this clearly."

Design a multi-stage, configurable pipeline.

### Stage A — Input Analysis

Analyze the original explanation.

Extract:

- Main topic.
- Primary claims.
- Important concepts.
- Prerequisite concepts.
- Technical vocabulary.
- Existing examples.
- Missing intermediate steps.
- Assumed prior knowledge.
- Possible sources of confusion.
- Ambiguous references.

Produce structured validated data.

### Stage B — Pedagogical Planning

Determine:

- Intended learner level.
- Essential learning objectives.
- Prerequisite ordering.
- Best explanation sequence.
- Necessary concrete examples.
- Whether an analogy is useful.
- Whether a diagram is useful.
- Appropriate detail level.

Do not assume all explanations require every technique.

### Stage C — Controlled Transformation

Rewrite or restructure the explanation according to selected experimental treatments.

Keep the treatment boundaries explicit so they can be independently evaluated.

For example, a vocabulary-only treatment should not secretly add a new analogy or radically restructure the conceptual sequence.

### Stage D — Fidelity Verification

Check:

- Preservation of factual claims.
- Preservation of numerical and technical details.
- Missing caveats.
- Newly introduced claims.
- Contradictions.
- Misleading analogies.
- Excessive information removal.

Store warnings and audit results.

### Stage E — Renderable Output

Return:

- Improved explanation.
- Applied treatments.
- Treatment-specific changes.
- Factual fidelity warnings.
- Optional concept graph.
- Optional explanatory diagram specification.
- Processing metadata.

Store structured outputs separately from rendered HTML.

Use safe Markdown rendering and sanitize generated content.

Do not allow arbitrary model-generated code to execute in the browser.

---

# 12. UI/UX Requirements

Build a polished, professional research interface.

Visual direction:

- Modern AI research workbench.
- Clean typography.
- Sophisticated spacing and information hierarchy.
- Minimal but purposeful color palette.
- Responsive desktop and mobile layouts.
- Smooth interaction states.
- Visually clear experimental configurations.
- High information density without visual clutter.

Avoid generic dashboard templates full of meaningless KPI cards.

Avoid excessive gradients, decorative animations, and fake visual sophistication.

Visual components must help researchers understand experiments.

## Required application areas

### A. Overview Dashboard

Display:

- Number of experiments.
- Completed runs.
- Models evaluated.
- Active human studies.
- API usage and estimated costs.
- Recent experiments.
- Evaluation coverage.

Do not populate real metrics with fabricated values.

### B. Experiment Studio

Primary workspace.

Include:

- Question input.
- Topic classification.
- Learner profile.
- Experiment selection.
- Model configuration.
- Prompt selection.
- Treatment selection.
- Run controls.
- Progress and error states.

### C. Answer Comparison Workspace

Provide:

- Side-by-side answer viewing.
- Raw and normalized rendering.
- Source and transformed variants.
- Model metadata.
- Explanation diagnostics.
- Differences and annotations.

Include a distraction-free reading mode.

### D. Pedagogical Analysis Workspace

Display:

- Extracted concepts.
- Prerequisite relationships.
- Concept dependency graph.
- Potential comprehension problems.
- Missing intermediate reasoning.
- Selected teaching strategy.

Use an interactive graph where useful.

Clearly label AI-inferred prerequisite relationships as hypotheses.

### E. Transformation Workbench

Allow researchers to:

- Select a source answer.
- Choose one or multiple transformations.
- Run the transformation.
- Inspect the transformed answer.
- View changes.
- Review fidelity warnings.
- Save variants.

### F. Human Evaluation Workspace

Researcher features:

- Create studies.
- Configure comprehension questions.
- Manage conditions.
- Generate participant links.
- Review submissions.
- Review anonymized results.

Participant features:

- Clean explanation reading screen.
- Comprehension questions.
- Usability and clarity feedback.
- No model-identifying metadata.

### G. Results and Analytics

Provide:

- Comparisons by experiment.
- Comparisons by model.
- Comparisons by transformation.
- Comparisons by topic.
- Comparisons by learner level.
- Comprehension performance.
- Reading-time analysis.
- Factual fidelity results.
- Cost and latency trade-offs.

Prefer charts that directly communicate findings.

### H. Research Library

Persist:

- Questions.
- Prompt templates.
- Answers.
- Experiment configurations.
- Transformation strategies.
- Study definitions.
- Evaluations.
- Generated reports.

Allow search, filtering, duplication, and exports.

---

# 13. Data Model

Design a relational schema supporting at least the following entities:

- Users / researchers.
- Learner profiles.
- Research questions.
- Models and providers.
- Prompt templates.
- Prompt versions.
- Experiments.
- Experiment conditions.
- Experiment runs.
- Raw responses.
- Transformed responses.
- Transformation strategies.
- Transformation versions.
- Concept graphs.
- Automated evaluations.
- Human studies.
- Study assignments.
- Participant responses.
- Assessment questions.
- Grading rubrics.
- Human assessment results.
- Usage and cost records.
- Research reports.

Avoid overengineering the schema, but preserve reproducibility and the relationships between source answers and transformed variants.

Use immutable experiment result records where practical.

Store raw outputs so researchers can re-evaluate them without repeatedly calling paid model APIs.

---

# 14. Seed Research Question Bank

Create a small configurable dataset with questions across multiple domains.

Use approximately 15 initial questions, expandable later.

Sample topics:

### Software Engineering

- How does Redis caching reduce database load?
- What happens when a browser sends an HTTPS request?
- How does a database transaction maintain consistency?
- Why does a race condition occur?
- How does a message queue improve reliability?

### AI/ML

- How does Retrieval-Augmented Generation work?
- Why are embeddings useful for semantic search?
- How does gradient descent update model parameters?
- What is the difference between training and inference?
- Why can an LLM hallucinate?

### Mathematics and Statistics

- Why is a p-value not the probability that a hypothesis is true?
- How does gradient descent find a minimum?
- Why does correlation not establish causation?

### Everyday Technical Concepts

- How does GPS determine location?
- Why does a refrigerator move heat from inside to outside?

Store questions and domain metadata.

For each question, allow a reviewed factual checklist identifying essential claims that a correct explanation should include.

Do not assume all test questions have equally difficult conceptual structures.

---

# 15. Experiment Execution and Reporting

Provide an experiment lifecycle:

`Draft → Configured → Running → Completed / Failed → Evaluated → Reported`

For each experiment:

- Validate the configuration.
- Display expected number of model requests.
- Execute independent requests.
- Track per-request completion.
- Save intermediate outputs.
- Handle failures gracefully.
- Support retry of failed tasks without duplicating completed records.
- Run evaluations when requested.
- Export results.

### Exports

Support:

- CSV.
- JSON.
- Human-readable Markdown report.

PDF export is optional if it complicates the initial implementation.

Report contents should include:

- Experiment objective.
- Hypothesis.
- Experimental conditions.
- Model and prompt configuration.
- Dataset and sample size.
- Evaluation methodology.
- Results.
- Limitations.
- Notable findings.
- Researcher notes.

### Evidence standard

Never claim that a model is better at teaching solely because an automated judge assigned a higher score.

Distinguish:

- Automated diagnostic results.
- AI judge opinions.
- Human preference results.
- Actual comprehension results.

---

# 16. Testing Requirements

Implement meaningful automated tests.

### Unit tests

Cover:

- Prompt rendering.
- Experiment configuration validation.
- Treatment selection.
- Provider response normalization.
- Concept graph schema validation.
- Automated metric calculations.
- Randomization logic.
- Scoring.
- Cost calculation.
- Export generation.

### Integration tests

Cover:

- Experiment creation.
- Model provider adapters using mocks.
- Response persistence.
- Transformation pipelines.
- Evaluation persistence.
- Human study submissions.
- Report generation.

### End-to-end tests

Verify at least:

1. Researcher creates a question.
2. Researcher configures a baseline experiment.
3. App generates or imports two model responses.
4. Responses appear in comparison view.
5. Researcher runs a transformation.
6. Transformed response is persisted.
7. Researcher creates a blind evaluation study.
8. Participant submits assessment.
9. Dashboard displays the stored result.

### Offline demonstration mode

Provide a clearly labeled demo mode using fixture responses.

The app should remain navigable without API keys.

Demo results must never be presented as actual research findings.

---

# 17. Scope and Implementation Priorities

Implement in vertical slices rather than building disconnected mock screens.

### Milestone 1 — Functional Foundation

- Project scaffolding.
- Database and migrations.
- API provider adapters.
- Research question management.
- Experiment creation.
- Raw response generation.
- Side-by-side comparison.
- Persistence.

### Milestone 2 — Controlled Experimentation

- Experiment 1: baseline.
- Experiment 2: prompting.
- Prompt versioning.
- Batch execution.
- Automated text diagnostics.
- Experiment metadata.

### Milestone 3 — Explanation Transformation

- Modular transformation pipeline.
- Individual treatments.
- Concept sequencing.
- Concept graph visualization.
- Fidelity checks.
- Experiment 3: ablation.
- Experiment 4: cross-model transformations.

### Milestone 4 — Human Comprehension Testing

- Human study builder.
- Participant interface.
- Blinded condition assignment.
- Comprehension assessments.
- Responses and scoring.
- Experiment 5.

### Milestone 5 — Analysis and Delivery

- Results dashboard.
- Charts.
- Reports and exports.
- Tests.
- Documentation.
- Deployment and setup instructions.

Every milestone should produce working, testable software.

If constraints prevent full implementation, prioritize complete core workflows over superficial breadth. Explicitly document unfinished features; never pretend an unimplemented experimental capability exists.

---

# 18. Security and Reliability

Implement:

- Server-side API secrets.
- Backend request validation.
- Reasonable input limits.
- Error handling.
- Provider timeouts.
- Safe retry limits.
- Secure rendering of generated text.
- Safe handling of participant submissions.
- Basic researcher authentication or restricted local deployment.
- Study access tokens that do not expose researcher controls.
- No public exposure of raw API keys.
- Protection against prompt injection in externally supplied research content.

Articles, imported explanations, and model outputs must be treated as untrusted data, never as privileged application instructions.

---

# 19. Required Documentation

Produce:

`README.md`

Installation, setup, commands, and usage.

`docs/PROJECT_OVERVIEW.md`

Problem, objectives, product roadmap, and boundaries.

`docs/RESEARCH_FOUNDATIONS.md`

Literature synthesis with citations, evidence levels, and limitations.

`docs/EXPERIMENT_DESIGN.md`

Detailed methodology for all five experiments, controls, scoring, and reproducibility.

`docs/ARCHITECTURE.md`

System structure, data flow, and integration boundaries.

`docs/TRANSFORMATION_ENGINE.md`

All transformation strategies, prompts, inputs, outputs, and fidelity checks.

`docs/DATABASE_SCHEMA.md`

Core entities and their relationships.

`docs/USER_GUIDE.md`

Step-by-step instructions for using the application and running each experiment.

`docs/KNOWN_LIMITATIONS.md`

Methodological, technical, and product limitations.

Also provide:

- `.env.example`
- Database migrations.
- Seed question dataset.
- Fixture data.
- Setup scripts.
- Test instructions.

---

# 20. Final Acceptance Criteria

The MVP is considered functionally complete when a researcher can:

1. Launch the application locally.
2. Configure OpenAI and Anthropic API credentials.
3. Create or select a research question.
4. Select models and learner profiles.
5. Run a baseline explanation comparison.
6. Run the three prompt-intervention conditions.
7. Apply individual pedagogical transformations.
8. Compare source and transformed answers.
9. Inspect a concept dependency graph.
10. Run cross-model transformations.
11. Create a blinded human evaluation study.
12. Share a participant assessment link.
13. Collect genuine comprehension results.
14. Inspect and compare experiment outcomes.
15. Export reproducible research data and a report.
16. Review API costs, errors, and generation metadata.

The system should function end to end, not merely show static mockups.

---

# 21. Crucial Product Principles

### Principle 1: Understanding over appearance

A visually appealing answer is not necessarily an understandable explanation.

### Principle 2: Explanation over simplification

Do not turn complex concepts into childish analogies or remove essential technical depth.

### Principle 3: Pedagogy over prompt decoration

We are investigating the actual processes that help humans learn.

### Principle 4: Reproducibility over anecdotes

Experiments should record conditions and use comparable evaluations.

### Principle 5: Human understanding over AI judge opinions

Automated scoring is useful, but actual comprehension evidence is more important.

### Principle 6: Model independence

The eventual transformation approach should not depend entirely on a single LLM provider.

### Principle 7: Research before product claims

Do not embed assumptions such as "ChatGPT is the better tutor" into scoring logic.

### Principle 8: Reusability

The transformation engine should later be reusable in a Claude Skill, standalone API, or browser extension.

---

# 22. Your Execution Instructions

Proceed as an autonomous implementation-oriented coding agent.

Follow this order:

**Step 1:** Research the supplied sources and relevant academic/technical references.

**Step 2:** Produce a concise evidence-based synthesis identifying the communication problems and testable mechanisms.

**Step 3:** Finalize the MVP architecture, database schema, experiment workflows, and interface design.

**Step 4:** Implement the full-stack application incrementally.

**Step 5:** Integrate OpenAI and Anthropic providers with configurable model identifiers.

**Step 6:** Implement experiments 1–5 and the modular transformation system.

**Step 7:** Implement human evaluation and analytics.

**Step 8:** Run automated tests and fix discovered problems.

**Step 9:** Document setup, usage, experiments, architecture, and limitations.

**Step 10:** Present the implemented features, actual test results, remaining limitations, and exact commands required to run the application.

Do not stop after generating a plan.

Do not replace actual software with pseudocode.

Do not use fake API responses except in clearly marked fixture/demo mode and automated tests.

Do not fabricate experimental conclusions.

Choose implementation approaches that are technically sound, maintainable, and practical for a solo developer continuing this project.

## Final Reminder

ExplanationLab is not an ordinary AI writing improver.

It is a research platform intended to discover, evaluate, and eventually operationalize mechanisms that transform technically competent LLM responses into explanations humans can genuinely understand.

**Build the tool that lets us discover the explanation mechanism before assuming we already know what that mechanism is.**
