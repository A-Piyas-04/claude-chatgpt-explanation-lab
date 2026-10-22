"""Prompt template rendering and versioning."""

from __future__ import annotations

import string

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import LearnerProfile, PromptTemplate, PromptVersion, ResearchQuestion
from .safety import GUARD_INSTRUCTION, untrusted_block


class _SafeFormatter(string.Formatter):
    """Leaves unknown placeholders intact instead of raising.

    Researchers edit these templates freely; a typo should produce visibly wrong
    text they can see and fix, not a 500 in the middle of a batch.
    """

    def get_value(self, key, args, kwargs):
        if isinstance(key, str):
            return kwargs.get(key, "{" + key + "}")
        return super().get_value(key, args, kwargs)


_FORMATTER = _SafeFormatter()


def profile_variables(profile: LearnerProfile | None) -> dict[str, str]:
    if profile is None:
        return {
            "learner_level": "unspecified",
            "learner_description": "No learner profile supplied.",
            "assumed_prior_knowledge": "unspecified",
            "unfamiliar_with": "unspecified",
            "learner_profile_name": "none",
        }
    return {
        "learner_level": profile.level,
        "learner_description": profile.description or "(no description)",
        "assumed_prior_knowledge": ", ".join(profile.assumed_prior_knowledge or []) or "unspecified",
        "unfamiliar_with": ", ".join(profile.unfamiliar_with or []) or "unspecified",
        "learner_profile_name": profile.name,
    }


def render(
    version: PromptVersion | None,
    question: ResearchQuestion,
    profile: LearnerProfile | None,
) -> tuple[str, str]:
    """Render (system, user) for a generation call.

    The question text is treated as untrusted data: it is wrapped in a delimited
    block and the system prompt carries the guard instruction. Research question
    banks can be shared between researchers, so this is not paranoia.
    """
    settings = get_settings()
    variables = profile_variables(profile)
    variables["domain"] = question.domain
    variables["topic"] = question.topic or question.domain

    system_raw = version.system_text if version else ""
    user_raw = version.user_template if version else "{question}"

    wrapped_question = untrusted_block(
        "research_question", question.text, max_chars=settings.max_input_chars
    )
    variables["question"] = wrapped_question

    user = _FORMATTER.vformat(user_raw, (), variables)
    system = _FORMATTER.vformat(system_raw, (), variables)

    # The guard is appended even to Condition A, whose system prompt is
    # otherwise empty. This is a documented, deliberate deviation from "no
    # system prompt at all": a security control we are not willing to drop.
    # It is recorded on every baseline response so the deviation is visible.
    system = (system + "\n\n" + GUARD_INSTRUCTION).strip() if system else GUARD_INSTRUCTION

    return system, user


BASELINE_GUARD_NOTE = (
    "A prompt-injection guard sentence is appended to the system prompt in every "
    "condition, including the default condition. This is a deliberate deviation "
    "from a literally empty system prompt, applied identically across conditions."
)


def get_template(db: Session, key: str) -> PromptTemplate | None:
    return db.execute(
        select(PromptTemplate).where(PromptTemplate.key == key)
    ).scalar_one_or_none()


def active_version(db: Session, template: PromptTemplate) -> PromptVersion | None:
    versions = sorted(template.versions, key=lambda v: v.version, reverse=True)
    for v in versions:
        if v.is_active:
            return v
    return versions[0] if versions else None


def version_by_key(db: Session, key: str) -> PromptVersion | None:
    template = get_template(db, key)
    if template is None:
        return None
    return active_version(db, template)


def add_version(
    db: Session,
    template: PromptTemplate,
    *,
    system_text: str,
    user_template: str,
    changelog: str = "",
) -> PromptVersion:
    """Append a new version. Existing versions are never mutated."""
    next_number = max((v.version for v in template.versions), default=0) + 1
    for v in template.versions:
        v.is_active = False
    version = PromptVersion(
        template_id=template.id,
        version=next_number,
        system_text=system_text,
        user_template=user_template,
        changelog=changelog,
        is_active=True,
    )
    db.add(version)
    db.flush()
    return version
