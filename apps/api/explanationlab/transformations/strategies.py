"""The six treatments of Experiment 3.

Each treatment is written to do **one thing**. The `boundary_note` and the
"Do not" block in each instruction exist because ablation is only meaningful if
the treatments are separable: if T1 quietly restructures the sequence, then a
"T1 vs T2" comparison measures nothing. Stage D checks for boundary violations
and the result is reported alongside the variant.

Template variables: ``{source_text}``, ``{question}``, ``{analysis}``,
``{plan}``, ``{learner_level}``, ``{learner_description}``,
``{assumed_prior_knowledge}``, ``{unfamiliar_with}``.
"""

from __future__ import annotations

from ..enums import Treatment
from .base import StrategyDefinition

_COMMON_TAIL = """
Output the rewritten explanation as Markdown, and nothing else. Do not describe
what you changed, do not add a preamble, do not add a closing summary.
"""

_PRESERVE = """
Hard constraints that apply regardless of treatment:
- Do not change any technical claim, formula, numeric value, unit, or named entity.
- Do not remove a caveat, limitation, or condition that the source states.
- Do not add certainty the source does not have. If the source hedges, keep the hedge.
- Do not invent facts, figures, benchmarks, or citations.
- If the source is wrong, leave it wrong. You are not fact-checking; you are
  changing how it is communicated. Flagging errors is Stage D's job, not yours.
"""

T1 = StrategyDefinition(
    key=Treatment.T1_VOCABULARY.value,
    name="Vocabulary and sentence clarification",
    category="language",
    description=(
        "Reduces lexical and syntactic load: unnecessary jargon, over-long sentences, "
        "indirect phrasing and unresolved references. Content and order untouched."
    ),
    boundary_note=(
        "Must not reorder concepts, add examples or analogies, add headings, or add "
        "mechanism detail. Sentence-level only."
    ),
    instruction_template="""\
Rewrite the explanation below to reduce the effort of reading it, **without
changing what it says or the order in which it says it**.

Do all of this:
1. Replace jargon that has a plain equivalent carrying the same meaning.
2. Keep technical terms that are genuinely load-bearing, but define each at
   first use, inline, in the sentence where it appears.
3. Split sentences that carry more than one idea. Prefer one claim per sentence.
4. Resolve ambiguous references: replace "it", "this", "that", "the former" with
   the thing they refer to wherever the referent is not immediately obvious.
5. Remove indirect constructions. Prefer "X causes Y" over "it is the case that
   Y may be understood as consequent upon X". Prefer the active voice.
6. Delete padding: restatements of the question, phrases like "it is worth
   noting that", "the operative consideration", self-congratulatory framing.

Do NOT do any of this:
- Do not change the order in which ideas appear.
- Do not add a new example, analogy, or comparison.
- Do not add headings, bullet lists, or tables that the source does not have.
- Do not add explanation of mechanism that the source does not contain.
- Do not shorten by dropping content. This treatment changes wording, not scope.

{preserve}

Learner level, for judging which terms count as jargon: {learner_level}
Probably unfamiliar with: {unfamiliar_with}

Explanation to rewrite:
{source_text}
{tail}""",
    default_params={"max_sentence_words": 28, "preserve_paragraph_breaks": True},
)

T2 = StrategyDefinition(
    key=Treatment.T2_SEQUENCING.value,
    name="Prerequisite-aware concept sequencing",
    category="structure",
    description=(
        "Reorders the explanation so no idea arrives before the ideas it depends on, "
        "using the concept dependency analysis. Wording left alone."
    ),
    boundary_note=(
        "Must not simplify vocabulary, add examples, or add formatting. Reordering and "
        "minimal connective tissue only. This is what makes H2 testable."
    ),
    instruction_template="""\
Reorganise the explanation below so that concepts arrive in a learnable order,
**without simplifying the language**.

You have a dependency analysis of the source:
{analysis}

And a teaching plan:
{plan}

Do all of this:
1. Order the material so that no concept is used before it has been introduced.
2. Where a prerequisite is needed but missing from the source, add the minimum
   needed to make the dependent idea follow — one or two sentences, no more.
3. Where two concepts are mutually dependent, say so explicitly rather than
   leaving the reader to notice the circularity.
4. Add only the connective sentences needed to make the new order read
   continuously ("now that X is in place, Y follows").
5. Keep every piece of content from the source somewhere in the result.

Do NOT do any of this:
- Do not simplify vocabulary or shorten sentences. Keep the source's wording for
  each piece of content; you are moving blocks, not rewriting them.
- Do not add examples, analogies, or diagrams.
- Do not add headings or lists unless the source already uses them.

{preserve}

Learner level: {learner_level}
Can be assumed to know: {assumed_prior_knowledge}

Explanation to reorganise:
{source_text}
{tail}""",
    default_params={"allow_minimal_bridging_sentences": True, "max_added_prerequisites": 3},
)

T3 = StrategyDefinition(
    key=Treatment.T3_MECHANISM.value,
    name="Mechanism and causal explanation",
    category="content",
    description=(
        "Turns description into mechanism: what happens, why, how the parts interact, "
        "and the intermediate steps the source skipped."
    ),
    boundary_note=(
        "Must not simplify vocabulary, reorder the overall structure, or add analogies. "
        "Adds causal detail in place."
    ),
    instruction_template="""\
Revise the explanation below so that it explains **how and why**, not only what.

Missing intermediate steps identified in the source:
{analysis}

Do all of this:
1. For each process described, make the steps explicit and in order. Where the
   source compresses several reasoning steps into one sentence, expand them.
2. State causes, not just correlations: what triggers what, and through what.
3. Describe how the components interact, including what each one is responsible
   for and what it needs from the others.
4. Distinguish clearly between a cause, an effect, a precondition, and an
   exception. Where the source conflates them, separate them.
5. Where a step is genuinely unknown or out of scope, say so rather than
   inventing a mechanism.

Do NOT do any of this:
- Do not invent a mechanism to fill a gap. If the source does not say how
  something works and you do not know, write that the source does not specify it.
- Do not simplify vocabulary or shorten sentences.
- Do not add analogies or real-world examples.
- Do not reorganise the overall order of the explanation.

{preserve}

Learner level: {learner_level}

Explanation to revise:
{source_text}
{tail}""",
    default_params={"expand_compressed_steps": True, "mark_unknown_mechanisms": True},
)

T4 = StrategyDefinition(
    key=Treatment.T4_EXAMPLES.value,
    name="Concrete examples and analogies",
    category="content",
    description=(
        "Adds one worked example and, if useful, one analogy — each explicitly mapped "
        "to the concept, with the limits of the mapping stated."
    ),
    boundary_note=(
        "Must not simplify vocabulary, reorder concepts, or add formatting. Adds "
        "grounding only, and only where the plan says it is warranted."
    ),
    instruction_template="""\
Add concrete grounding to the explanation below.

The pedagogical plan for this explanation says:
{plan}

If the plan says an analogy or example is not needed, **do not add one** — return
the explanation with only the grounding the plan calls for. Not every concept
needs an analogy, and a decorative one makes the explanation worse.

When you do add grounding:
1. Use one realistic example drawn from a context this learner plausibly knows.
   Prefer a case a practitioner would actually meet over a toy illustration.
2. Immediately state how the example maps onto the general concept — which part
   of the example corresponds to which part of the mechanism.
3. State where the mapping stops holding. Every analogy breaks somewhere, and an
   unmarked breaking point is how misconceptions form.
4. Keep it to one example and at most one analogy. Several competing
   illustrations add load rather than removing it.

Do NOT do any of this:
- Do not use childish or patronising comparisons. This is an adult who knows
  other things. No toys, no sweets, no "imagine you are a tiny packet".
- Do not add an example that is unrelated to the mechanism being explained.
- Do not simplify vocabulary, reorder concepts, or add headings.
- Do not invent factual specifics (benchmarks, figures, company behaviour) to
  make an example concrete. Keep invented detail to the illustrative scenario
  itself, and keep it obviously illustrative.

{preserve}

Learner level: {learner_level}
Can be assumed to know: {assumed_prior_knowledge}

Explanation to ground:
{source_text}
{tail}""",
    default_params={"max_examples": 1, "max_analogies": 1, "require_mapping_statement": True},
)

T5 = StrategyDefinition(
    key=Treatment.T5_STRUCTURE.value,
    name="Structural and visual presentation",
    category="presentation",
    description=(
        "Applies structure that reveals the conceptual shape: headings, short "
        "paragraphs, ordered steps for procedures, a table where a comparison is "
        "genuinely being made, and a diagram specification where flow matters."
    ),
    boundary_note=(
        "Must not change wording, order, or content. Pure presentation — this is what "
        "makes H3 (presentation vs comprehension) testable."
    ),
    instruction_template="""\
Re-present the explanation below so its structure reveals the structure of the
**ideas**, without changing the words more than the format requires.

Do all of this:
1. Add headings that name what each section establishes. A heading should say
   what the reader will know after it, not merely label a topic.
2. Break long paragraphs so each covers one idea.
3. Where the source describes a procedure or sequence, render it as ordered steps.
4. Where the source genuinely compares two or more things along shared
   dimensions, render that as a table. If there is no real comparison, do not
   invent one to have a table.
5. Where the source describes a flow or a mechanism with moving parts, append a
   fenced block labelled `diagram` containing a simple node-and-arrow
   specification, one edge per line, in the form `A -> B: label`.

Do NOT do any of this:
- Do not rewrite sentences for clarity, simplify vocabulary, or shorten prose.
- Do not reorder the content.
- Do not add or remove information.
- Do not add structure for its own sake. A short explanation that is already one
  clear idea should come back close to unchanged. Formatting that does not
  reflect a real conceptual boundary adds noise.

{preserve}

Explanation to re-present:
{source_text}
{tail}""",
    default_params={"allow_tables": True, "allow_diagram_spec": True, "max_heading_depth": 3},
)

T6 = StrategyDefinition(
    key=Treatment.T6_AUDIENCE.value,
    name="Audience adaptation",
    category="audience",
    description=(
        "Re-pitches the explanation for a specific learner profile by changing what is "
        "assumed and what is unpacked — not by changing the facts."
    ),
    boundary_note=(
        "Must not change technical content. Adjusts assumed prior knowledge and depth "
        "of unpacking only. Expect the expertise-reversal effect: more scaffolding "
        "should help beginners and hinder advanced learners."
    ),
    instruction_template="""\
Re-pitch the explanation below for this specific learner.

Learner profile:
- Level: {learner_level}
- Description: {learner_description}
- Can be assumed to know: {assumed_prior_knowledge}
- Probably unfamiliar with: {unfamiliar_with}

The source currently assumes:
{analysis}

Do all of this:
1. For anything in "probably unfamiliar with" that the explanation relies on,
   introduce it before it is used.
2. For anything in "can be assumed to know", do not explain it. Spelling out
   what this learner already holds wastes their attention and reads as
   condescension.
3. Adjust how far each idea is unpacked to match the level — more intermediate
   steps for a beginner, more compression and more precise terminology for an
   advanced learner.
4. Keep the facts identical at every level. A beginner and an advanced learner
   should come away with the same model of how the thing works, differing in
   detail and not in substance.

Do NOT do any of this:
- Do not change, soften, or drop technical claims to suit the level.
- Do not patronise a beginner. Adapting is not simplifying the content.
- Do not add examples or analogies unless removing an unexplained prerequisite
  requires one.
- Do not reorganise beyond what introducing a prerequisite requires.

{preserve}

Explanation to re-pitch:
{source_text}
{tail}""",
    default_params={"respect_assumed_knowledge": True},
)


ALL_STRATEGIES: list[StrategyDefinition] = [T1, T2, T3, T4, T5, T6]
STRATEGY_BY_KEY: dict[str, StrategyDefinition] = {s.key: s for s in ALL_STRATEGIES}


def render_instruction(
    strategy: StrategyDefinition,
    *,
    source_text: str,
    question: str = "",
    analysis: str = "(no analysis available)",
    plan: str = "(no plan available)",
    learner_level: str = "unspecified",
    learner_description: str = "",
    assumed_prior_knowledge: str = "unspecified",
    unfamiliar_with: str = "unspecified",
) -> str:
    return strategy.instruction_template.format(
        source_text=source_text,
        question=question,
        analysis=analysis,
        plan=plan,
        learner_level=learner_level,
        learner_description=learner_description,
        assumed_prior_knowledge=assumed_prior_knowledge,
        unfamiliar_with=unfamiliar_with,
        preserve=_PRESERVE,
        tail=_COMMON_TAIL,
    )


def ordered_treatments(keys: list[str]) -> list[StrategyDefinition]:
    """Compose treatments in a defensible fixed order.

    Order matters when treatments are combined, and an arbitrary order would be
    an uncontrolled variable. We apply content-adding treatments before
    presentation ones, and language polish before reordering, so that later
    stages operate on the fuller text:

        T3 (mechanism) -> T4 (examples) -> T6 (audience) -> T1 (language)
        -> T2 (sequencing) -> T5 (presentation)

    The pipeline records this order on every combined variant, and a researcher
    can override it per condition.
    """
    canonical = [
        Treatment.T3_MECHANISM.value,
        Treatment.T4_EXAMPLES.value,
        Treatment.T6_AUDIENCE.value,
        Treatment.T1_VOCABULARY.value,
        Treatment.T2_SEQUENCING.value,
        Treatment.T5_STRUCTURE.value,
    ]
    requested = [k for k in keys if k in STRATEGY_BY_KEY]
    return [STRATEGY_BY_KEY[k] for k in canonical if k in requested]
