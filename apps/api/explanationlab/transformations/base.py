"""Transformation engine contracts.

This package is deliberately free of FastAPI and SQLAlchemy imports in its
core logic (schemas, strategy definitions, prompt construction) so that it can
later be lifted into a Claude Skill, a standalone API, or a browser extension
without dragging the research platform with it — Stage 2-4 of the roadmap and
Principle 8.

The only platform coupling is the ``call_structured`` gateway function passed in
by the caller, which is a two-argument callable, not a framework object.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass(slots=True)
class StrategyDefinition:
    """One independently applicable treatment."""

    key: str
    name: str
    category: str
    description: str
    # What this treatment must NOT do. Enforced in the prompt and checked in
    # Stage D, because ablation is meaningless if T1 quietly also does T4's job.
    boundary_note: str
    instruction_template: str
    default_params: dict = field(default_factory=dict)
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    version: int = 1


def schema_instruction(schema: dict, name: str) -> str:
    """Describe a JSON schema in the prompt as well as in the API parameter.

    Belt and braces: native structured output is used where the model supports
    it, but a model that rejects the parameter still needs to know the shape.
    """
    return (
        f"Reply with a single JSON object named {name}, matching this JSON Schema "
        f"exactly. No prose outside the JSON, no code fence.\n\n"
        f"{json.dumps(schema, indent=2)}"
    )


# ---------------------------------------------------------------------------
# Stage A — Input analysis schema
# ---------------------------------------------------------------------------

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "main_topic": {"type": "string"},
        "primary_claims": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Technical assertions the explanation makes. Used by Stage D.",
        },
        "key_concepts": {"type": "array", "items": {"type": "string"}},
        "prerequisite_concepts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Concepts a reader must already hold for the text to make sense.",
        },
        "technical_vocabulary": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "explained_in_text": {"type": "boolean"},
                    "necessary": {
                        "type": "boolean",
                        "description": "False if a plainer word carries the same meaning.",
                    },
                },
                "required": ["term", "explained_in_text"],
            },
        },
        "existing_examples": {"type": "array", "items": {"type": "string"}},
        "missing_intermediate_steps": {"type": "array", "items": {"type": "string"}},
        "assumed_prior_knowledge": {"type": "array", "items": {"type": "string"}},
        "possible_confusions": {"type": "array", "items": {"type": "string"}},
        "ambiguous_references": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Pronouns or deictic phrases whose referent is unclear.",
        },
    },
    "required": [
        "main_topic",
        "primary_claims",
        "key_concepts",
        "prerequisite_concepts",
        "technical_vocabulary",
    ],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# Stage B — Pedagogical plan schema
# ---------------------------------------------------------------------------

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "learner_level": {"type": "string", "enum": ["beginner", "intermediate", "advanced"]},
        "learning_objectives": {"type": "array", "items": {"type": "string"}},
        "prerequisite_order": {"type": "array", "items": {"type": "string"}},
        "explanation_sequence": {"type": "array", "items": {"type": "string"}},
        "needs_concrete_example": {"type": "boolean"},
        "needs_analogy": {"type": "boolean"},
        "needs_diagram": {"type": "boolean"},
        "analogy_rationale": {"type": "string"},
        "detail_level": {"type": "string", "enum": ["minimal", "moderate", "thorough"]},
        "techniques_not_needed": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Techniques this particular explanation does NOT need, and why.",
        },
    },
    "required": [
        "learner_level",
        "learning_objectives",
        "prerequisite_order",
        "explanation_sequence",
        "needs_concrete_example",
        "needs_analogy",
        "needs_diagram",
        "detail_level",
    ],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# Stage D — Fidelity schema
# ---------------------------------------------------------------------------

FIDELITY_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["clean", "warnings", "serious_concerns"]},
        "warnings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": [
                            "altered_claim",
                            "new_claim",
                            "omitted_claim",
                            "omitted_caveat",
                            "numeric_change",
                            "contradiction",
                            "misleading_analogy",
                            "false_simplification",
                            "unjustified_certainty",
                            "information_loss",
                        ],
                    },
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "detail": {"type": "string"},
                    "source_excerpt": {"type": "string"},
                    "transformed_excerpt": {"type": "string"},
                },
                "required": ["type", "severity", "detail"],
            },
        },
        "numeric_drift": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_value": {"type": "string"},
                    "transformed_value": {"type": "string"},
                    "context": {"type": "string"},
                },
                "required": ["source_value", "transformed_value"],
            },
        },
        "preserved_claims": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
    },
    "required": ["verdict", "warnings"],
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# Concept graph schema
# ---------------------------------------------------------------------------

CONCEPT_GRAPH_SCHEMA = {
    "type": "object",
    "properties": {
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "importance": {
                        "type": "string",
                        "enum": ["core", "supporting", "optional"],
                    },
                    "introduced_in_text": {"type": "boolean"},
                    "explained_in_text": {"type": "boolean"},
                },
                "required": ["id", "label"],
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "relation": {
                        "type": "string",
                        "enum": ["prerequisite_for", "motivates", "contrasts_with", "part_of"],
                    },
                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": ["source", "target", "relation"],
            },
        },
        "notes": {"type": "string"},
    },
    "required": ["nodes", "edges"],
    "additionalProperties": False,
}
