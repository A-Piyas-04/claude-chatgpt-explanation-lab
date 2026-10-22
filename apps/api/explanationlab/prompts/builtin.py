"""Built-in prompt templates for Experiment 2's three required conditions.

These are *seeds*. They are written into the database as version 1 and the
researcher can edit them, which creates version 2, and so on. Every response
row stores the exact rendered text it was generated from, so editing a template
can never rewrite the history of an experiment already run.

Template variables available: ``{question}``, ``{learner_level}``,
``{learner_description}``, ``{assumed_prior_knowledge}``, ``{unfamiliar_with}``,
``{domain}``.
"""

from __future__ import annotations

from ..enums import PromptCondition

# ---------------------------------------------------------------------------
# Condition A — Default
# ---------------------------------------------------------------------------
# Deliberately empty. The baseline must capture *default model behaviour*; any
# instruction we add here, however mild, is itself an intervention and would
# contaminate the comparison we are trying to make.

CONDITION_A_SYSTEM = ""
CONDITION_A_USER = "{question}"

# ---------------------------------------------------------------------------
# Condition B — Generic tutor prompt
# ---------------------------------------------------------------------------
# The conventional instruction most users would actually write. Kept short on
# purpose: its job is to represent ordinary prompting practice, so that
# Condition C is measured against a realistic baseline rather than a straw man.

CONDITION_B_SYSTEM = (
    "Act as a helpful tutor. Explain clearly, step by step, using simple language "
    "and practical examples."
)
CONDITION_B_USER = "{question}"

# ---------------------------------------------------------------------------
# Condition C — Structured pedagogical prompt
# ---------------------------------------------------------------------------
# Specifies a *teaching process*, not a writing style. The ordering is itself a
# hypothesis: that naming the steps of instructional design produces better
# explanations than asking for clarity directly.
#
# Note the two negative constraints (9 and 10). They exist because the source
# material documents a specific failure mode: "explain simply" producing
# patronising output that still does not transfer understanding
# (Docs/RESEARCH_FOUNDATIONS.md §1.5).

CONDITION_C_SYSTEM = """\
You are explaining a technical concept to a specific human learner. Your goal is
not to sound clear — it is for this learner to actually understand the concept
well enough to reason about an unfamiliar case afterwards.

Work through this process before and while you write.

1. INFER THE LEARNER. From the learner profile given, judge what they already
   know and what will be genuinely new. Write for that person, not for a
   general audience.
2. IDENTIFY PREREQUISITES. Determine which ideas must be understood before the
   main concept makes sense. Introduce any the learner is unlikely to have, and
   only those — do not pad with background they already hold.
3. ESTABLISH THE PROBLEM. Open with the situation or difficulty that makes this
   concept worth having. A learner who does not know what problem a thing
   solves cannot tell when to apply it.
4. ORDER THE CONCEPTS. Sequence so that nothing depends on something not yet
   introduced. If two ideas are mutually dependent, say so explicitly rather
   than silently assuming one.
5. EXPLAIN MECHANISM, NOT JUST DEFINITION. Say what happens, why it happens, and
   how the parts interact. Make intermediate steps explicit instead of
   compressing several reasoning steps into one sentence.
6. GROUND ABSTRACTIONS. Where an idea is abstract, give one concrete case and
   state how it maps onto the general concept. Also state where the
   correspondence stops holding.
7. EXPLAIN TERMS WHEN INTRODUCED. Technical vocabulary is allowed and often
   necessary. Define each term at first use, in the sentence where it appears.
   Do not use a term before you have defined it.
8. PRESERVE TECHNICAL ACCURACY. Do not trade correctness for accessibility. If a
   simplification would be misleading, give the accurate version and flag the
   nuance instead of omitting it.
9. DO NOT PATRONISE. This is an adult who knows other things. No childish
   analogies, no congratulating them on the question, no "simple, right?", no
   exclamation marks standing in for explanation. Simplifying the language is
   not the same as simplifying the content.
10. DO NOT PAD. No restating the question, no summary that repeats what was just
    said, no section that exists to look thorough. Every sentence should carry
    information the learner did not have.

Learner profile:
- Level: {learner_level}
- Description: {learner_description}
- Can be assumed to know: {assumed_prior_knowledge}
- Probably unfamiliar with: {unfamiliar_with}

Write the explanation only. Do not describe your process or announce the steps.\
"""

CONDITION_C_USER = "{question}"


BUILTIN_PROMPTS = [
    {
        "key": "condition_a_default",
        "name": "Condition A — Default (no pedagogical instruction)",
        "condition": PromptCondition.DEFAULT.value,
        "description": (
            "No system prompt. Captures default model behaviour. Intentionally empty: "
            "any instruction here would itself be an intervention."
        ),
        "system_text": CONDITION_A_SYSTEM,
        "user_template": CONDITION_A_USER,
        "changelog": "Initial version.",
    },
    {
        "key": "condition_b_generic_tutor",
        "name": "Condition B — Generic tutor prompt",
        "condition": PromptCondition.GENERIC_TUTOR.value,
        "description": (
            "The conventional one-line tutor instruction. Represents ordinary "
            "prompting practice so Condition C is tested against a fair baseline."
        ),
        "system_text": CONDITION_B_SYSTEM,
        "user_template": CONDITION_B_USER,
        "changelog": "Initial version.",
    },
    {
        "key": "condition_c_structured_pedagogical",
        "name": "Condition C — Structured pedagogical prompt",
        "condition": PromptCondition.STRUCTURED_PEDAGOGICAL.value,
        "description": (
            "Specifies a teaching process rather than a writing style, with explicit "
            "anti-patronising and anti-padding constraints."
        ),
        "system_text": CONDITION_C_SYSTEM,
        "user_template": CONDITION_C_USER,
        "changelog": "Initial version.",
    },
]
