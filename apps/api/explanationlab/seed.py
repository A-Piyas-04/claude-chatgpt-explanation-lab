"""Idempotent database seeding.

Run directly:

    python -m explanationlab.seed

Re-running is safe: existing rows are updated in place rather than duplicated,
and researcher-authored prompt versions are never overwritten (a built-in
template that has been edited keeps the edit).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import create_all, session_scope
from .enums import LearnerLevel
from .models import (
    GradingRubric,
    LearnerProfile,
    ModelCatalogEntry,
    PromptTemplate,
    PromptVersion,
    Researcher,
    ResearchQuestion,
    TransformationStrategy,
    TransformationVersion,
)
from .prompts.builtin import BUILTIN_PROMPTS
from .providers.catalog import seed_rows
from .evaluation.rubrics import SHORT_ANSWER_RUBRICS
from .transformations.strategies import ALL_STRATEGIES

log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"

BUILTIN_PROFILES = [
    {
        "name": "Beginner — new to the field",
        "level": LearnerLevel.BEGINNER.value,
        "description": (
            "An adult who is capable and curious but new to this subject area. Has "
            "general computer literacy and no formal background in the topic."
        ),
        "assumed_prior_knowledge": [
            "everyday use of software and websites",
            "basic arithmetic",
        ],
        "unfamiliar_with": [
            "domain-specific terminology",
            "standard architectural patterns",
            "mathematical notation beyond basic algebra",
        ],
    },
    {
        "name": "Intermediate — working practitioner",
        "level": LearnerLevel.INTERMEDIATE.value,
        "description": (
            "A practising professional with two to five years of general experience "
            "who has not worked specifically on this topic."
        ),
        "assumed_prior_knowledge": [
            "programming in at least one language",
            "client-server request flow",
            "reading technical documentation",
            "basic statistics",
        ],
        "unfamiliar_with": [
            "specialist sub-domain vocabulary",
            "formal proofs",
            "implementation internals",
        ],
    },
    {
        "name": "Advanced — domain specialist",
        "level": LearnerLevel.ADVANCED.value,
        "description": (
            "An experienced specialist who knows adjacent material well and wants "
            "precision and mechanism, not scaffolding. Will find basic background "
            "explanations wasteful."
        ),
        "assumed_prior_knowledge": [
            "standard terminology of the field",
            "common architectural and mathematical patterns",
            "trade-off reasoning",
            "formal notation",
        ],
        "unfamiliar_with": ["the specific mechanism under discussion"],
    },
    {
        "name": "Non-native English reader — intermediate domain knowledge",
        "level": LearnerLevel.INTERMEDIATE.value,
        "description": (
            "A competent practitioner reading in a second language. Technical "
            "concepts are not the barrier; unusual vocabulary, idiom, long "
            "subordinate clauses and indirect phrasing are. Included because the "
            "source material repeatedly identifies this group as worst affected "
            "(Docs/RESEARCH_FOUNDATIONS.md §1.1)."
        ),
        "assumed_prior_knowledge": [
            "programming experience",
            "standard technical terminology in written form",
        ],
        "unfamiliar_with": [
            "English idiom and colloquialism",
            "low-frequency latinate vocabulary",
            "long sentences with multiple subordinate clauses",
        ],
    },
]


def seed_all(db: Session) -> dict:
    counts = {
        "researchers": _seed_researcher(db),
        "learner_profiles": _seed_profiles(db),
        "research_questions": _seed_questions(db),
        "model_catalog": _seed_models(db),
        "prompt_templates": _seed_prompts(db),
        "transformation_strategies": _seed_strategies(db),
        "grading_rubrics": _seed_rubrics(db),
    }
    db.flush()
    return counts


def _seed_researcher(db: Session) -> int:
    existing = db.execute(select(Researcher)).scalars().first()
    if existing is not None:
        return 0
    db.add(Researcher(email="researcher@localhost", name="Local Researcher"))
    return 1


def _seed_profiles(db: Session) -> int:
    added = 0
    for payload in BUILTIN_PROFILES:
        existing = db.execute(
            select(LearnerProfile).where(LearnerProfile.name == payload["name"])
        ).scalar_one_or_none()
        if existing is None:
            db.add(LearnerProfile(**payload, is_builtin=True))
            added += 1
        else:
            existing.level = payload["level"]
            existing.description = payload["description"]
            existing.assumed_prior_knowledge = payload["assumed_prior_knowledge"]
            existing.unfamiliar_with = payload["unfamiliar_with"]
    return added


def _seed_questions(db: Session) -> int:
    path = DATA_DIR / "seed_questions.json"
    if not path.exists():
        log.warning("Seed question file missing: %s", path)
        return 0

    payload = json.loads(path.read_text(encoding="utf-8"))
    added = 0
    for item in payload.get("questions", []):
        existing = db.execute(
            select(ResearchQuestion).where(ResearchQuestion.text == item["text"])
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                ResearchQuestion(
                    text=item["text"],
                    domain=item.get("domain", "general"),
                    topic=item.get("topic", ""),
                    conceptual_difficulty=item.get("conceptual_difficulty", "unrated"),
                    factual_checklist=item.get("factual_checklist", []),
                    checklist_reviewed_by="project author (initial pass)",
                    is_seed=True,
                )
            )
            added += 1
        else:
            existing.factual_checklist = item.get("factual_checklist", [])
            existing.conceptual_difficulty = item.get("conceptual_difficulty", "unrated")
    return added


def _seed_models(db: Session) -> int:
    added = 0
    for row in seed_rows():
        existing = db.execute(
            select(ModelCatalogEntry).where(
                ModelCatalogEntry.provider == row["provider"],
                ModelCatalogEntry.model_id == row["model_id"],
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(ModelCatalogEntry(**row))
            added += 1
        else:
            # Refresh capability and pricing facts, keep the enable/disable
            # choice the operator made.
            for key, value in row.items():
                if key != "is_enabled":
                    setattr(existing, key, value)
    return added


def _seed_prompts(db: Session) -> int:
    added = 0
    for payload in BUILTIN_PROMPTS:
        template = db.execute(
            select(PromptTemplate).where(PromptTemplate.key == payload["key"])
        ).scalar_one_or_none()
        if template is None:
            template = PromptTemplate(
                key=payload["key"],
                name=payload["name"],
                condition=payload["condition"],
                description=payload["description"],
                is_builtin=True,
            )
            db.add(template)
            db.flush()
            db.add(
                PromptVersion(
                    template_id=template.id,
                    version=1,
                    system_text=payload["system_text"],
                    user_template=payload["user_template"],
                    changelog=payload["changelog"],
                    is_active=True,
                )
            )
            added += 1
        else:
            # Never clobber a researcher's edits: metadata only.
            template.name = payload["name"]
            template.description = payload["description"]
            template.condition = payload["condition"]
    return added


def _seed_strategies(db: Session) -> int:
    added = 0
    for definition in ALL_STRATEGIES:
        strategy = db.execute(
            select(TransformationStrategy).where(TransformationStrategy.key == definition.key)
        ).scalar_one_or_none()
        if strategy is None:
            strategy = TransformationStrategy(
                key=definition.key,
                name=definition.name,
                description=definition.description,
                category=definition.category,
                boundary_note=definition.boundary_note,
                is_builtin=True,
            )
            db.add(strategy)
            db.flush()
            db.add(
                TransformationVersion(
                    strategy_id=strategy.id,
                    version=definition.version,
                    instruction_template=definition.instruction_template,
                    input_schema=definition.input_schema,
                    output_schema=definition.output_schema,
                    default_params=definition.default_params,
                    changelog="Initial version.",
                    is_active=True,
                )
            )
            added += 1
        else:
            strategy.name = definition.name
            strategy.description = definition.description
            strategy.category = definition.category
            strategy.boundary_note = definition.boundary_note
    return added


def _seed_rubrics(db: Session) -> int:
    added = 0
    for payload in SHORT_ANSWER_RUBRICS:
        existing = db.execute(
            select(GradingRubric).where(
                GradingRubric.key == payload["key"],
                GradingRubric.version == payload["version"],
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                GradingRubric(
                    key=payload["key"],
                    version=payload["version"],
                    name=payload["name"],
                    criteria=payload["criteria"],
                    max_score=payload["max_score"],
                )
            )
            added += 1
    return added


def main() -> None:  # pragma: no cover - entry point
    logging.basicConfig(level=logging.INFO, format="%(levelname)-5s %(message)s")
    create_all()
    with session_scope() as db:
        counts = seed_all(db)
    log.info("Seed complete: %s", counts)
    print("Seeded:", json.dumps(counts, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
