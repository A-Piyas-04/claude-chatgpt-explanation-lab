"""Explicit scoring rubrics.

Anchored 1-5 scales. Anchors matter: an unanchored "rate clarity 1-5" produces a
judge that regresses to 4 and tells you nothing.

Note what is deliberately absent: there is no composite "overall quality" score.
Dimensions that measure different things (perceived clarity vs mechanism
coverage) are not averaged, because the fluency literature shows they can move
in opposite directions (Docs/RESEARCH_FOUNDATIONS.md §2).
"""

from __future__ import annotations

JUDGE_RUBRIC_KEY = "explanation_quality"
JUDGE_RUBRIC_VERSION = 1

JUDGE_DIMENSIONS = [
    {
        "metric": "clarity",
        "question": "Can each individual statement be understood on first reading?",
        "anchors": {
            1: "Most sentences require re-reading; dense or convoluted throughout.",
            3: "Generally followable; several sentences carry too many ideas at once.",
            5: "Each sentence lands on first reading without loss of precision.",
        },
    },
    {
        "metric": "logical_progression",
        "question": "Does each part follow from what came before?",
        "anchors": {
            1: "Ideas appear in an order that does not build; jumps are frequent.",
            3: "Mostly ordered, with some ideas arriving before their groundwork.",
            5: "Every step rests on something already established.",
        },
    },
    {
        "metric": "prerequisite_handling",
        "question": "Are concepts the reader needs first actually provided first?",
        "anchors": {
            1: "Relies throughout on knowledge it never supplies.",
            3: "Supplies some prerequisites; assumes others silently.",
            5: "Needed prerequisites are introduced before use, without padding.",
        },
    },
    {
        "metric": "mechanism_explanation",
        "question": "Does it explain how and why, not only what?",
        "anchors": {
            1: "Definitions and assertions only; no causal account.",
            3: "Some mechanism, with intermediate steps left implicit.",
            5: "Causes, interactions and intermediate steps are explicit.",
        },
    },
    {
        "metric": "example_quality",
        "question": "If examples or analogies are used, do they aid understanding?",
        "anchors": {
            1: "Examples are decorative, unrelated, or actively misleading.",
            3: "Relevant examples, but the mapping to the concept is left implicit.",
            5: "Example is apt, mapped explicitly, and its limits are stated. "
            "Score 5 also applies if no example was needed and none was given.",
        },
    },
    {
        "metric": "audience_suitability",
        "question": "Is it pitched at the stated learner, neither over nor under their head?",
        "anchors": {
            1: "Badly mismatched: unexplained expert content, or patronising basics.",
            3: "Roughly right with stretches that miss the level.",
            5: "Consistently pitched at the stated learner.",
        },
    },
    {
        "metric": "unnecessary_complexity",
        "question": "Is complexity intrinsic to the subject rather than added by the writing? "
        "(5 = no added complexity)",
        "anchors": {
            1: "Heavy added complexity: avoidable jargon, indirection, padding.",
            3: "Some avoidable density.",
            5: "All remaining difficulty belongs to the subject itself.",
        },
    },
    {
        "metric": "information_loss",
        "question": "Is substantive content preserved rather than dropped? (5 = nothing lost)",
        "anchors": {
            1: "Essential content, caveats or qualifications are missing.",
            3: "Minor detail lost.",
            5: "Content is intact; any simplification is of expression, not substance.",
        },
    },
    {
        "metric": "factual_fidelity",
        "question": "Is it internally consistent and free of claims it cannot support? "
        "(5 = no problems detected)",
        "anchors": {
            1: "Contains claims that contradict each other or are plainly unsupported.",
            3: "Mostly sound with one or two questionable assertions.",
            5: "No problems detected. This is not verification of correctness.",
        },
    },
]

SHORT_ANSWER_RUBRICS = [
    {
        "key": "mechanism_short_answer",
        "version": 1,
        "name": "Mechanistic understanding — short answer",
        "max_score": 2.0,
        "criteria": [
            {
                "score": 0,
                "label": "No mechanism",
                "descriptor": "Restates what happens with no account of how or why, or is incorrect.",
            },
            {
                "score": 1,
                "label": "Partial mechanism",
                "descriptor": "Identifies the right components or direction but omits a necessary step.",
            },
            {
                "score": 2,
                "label": "Correct mechanism",
                "descriptor": "States the causal chain with the necessary intermediate steps.",
            },
        ],
    },
    {
        "key": "transfer_scenario",
        "version": 1,
        "name": "Transfer — scenario application",
        "max_score": 2.0,
        "criteria": [
            {
                "score": 0,
                "label": "No transfer",
                "descriptor": "Repeats the explanation without applying it, or applies it wrongly.",
            },
            {
                "score": 1,
                "label": "Partial transfer",
                "descriptor": "Reaches a defensible answer but the reasoning is incomplete.",
            },
            {
                "score": 2,
                "label": "Successful transfer",
                "descriptor": "Applies the principle correctly to the new case with sound reasoning.",
            },
        ],
    },
]


def rubric_text() -> str:
    lines = []
    for d in JUDGE_DIMENSIONS:
        lines.append(f"- **{d['metric']}** — {d['question']}")
        for score, anchor in sorted(d["anchors"].items()):
            lines.append(f"    {score}: {anchor}")
    return "\n".join(lines)


JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "enum": [d["metric"] for d in JUDGE_DIMENSIONS],
                    },
                    "score": {"type": "integer", "minimum": 1, "maximum": 5},
                    "rationale": {"type": "string"},
                    "evidence": {
                        "type": "string",
                        "description": "A verbatim span from the explanation supporting the score.",
                    },
                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                    "improvement_suggestion": {"type": "string"},
                },
                "required": ["metric", "score", "rationale", "evidence", "confidence"],
            },
        },
        "overall_notes": {"type": "string"},
    },
    "required": ["scores"],
    "additionalProperties": False,
}

GRADING_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "number"},
        "rationale": {"type": "string"},
        "misconception_detected": {"type": "boolean"},
        "misconception_detail": {"type": "string"},
    },
    "required": ["score", "rationale", "misconception_detected"],
    "additionalProperties": False,
}
