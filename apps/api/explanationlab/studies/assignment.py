"""Blinded, seeded, balanced condition assignment.

Four requirements from §6 Experiment 5, and how each is met:

- *participants must not see model identities or treatment names* — the
  participant payload is built by :func:`participant_view`, which selects only
  the explanation text. Researcher-facing labels live on a different object.
- *randomised allocation* — :func:`choose_condition`.
- *seeded randomisation for reproducibility* — the study's ``seed`` plus the
  participant code; the same participant in the same study always lands in the
  same arm, and the whole allocation sequence is replayable.
- *balance condition counts where practical* — least-filled-arm-first, with
  random tie-breaking rather than always picking the first.
- *avoid giving the same learner multiple explanations of the same concept
  before assessment* — :func:`check_repeat_exposure`.
"""

from __future__ import annotations

import hashlib
import random
import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..enums import AssignmentStatus, StudyStatus
from ..models import (
    AssessmentItem,
    ParticipantSubmission,
    Study,
    StudyAssignment,
    StudyCondition,
)


class StudyClosedError(RuntimeError):
    pass


class RepeatExposureError(RuntimeError):
    pass


class NoEligibleConditionError(RuntimeError):
    pass


def new_participant_code() -> str:
    """Anonymous identifier. Carries no personal information."""
    return "P-" + secrets.token_hex(6).upper()


def _rng_for(study: Study, participant_code: str) -> random.Random:
    digest = hashlib.sha256(f"{study.seed}:{study.id}:{participant_code}".encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def condition_counts(db: Session, study_id: str) -> dict[str, int]:
    """Assignments per arm, excluding withdrawals."""
    rows = db.execute(
        select(StudyAssignment.condition_id, func.count(StudyAssignment.id))
        .where(
            StudyAssignment.study_id == study_id,
            StudyAssignment.status != AssignmentStatus.WITHDRAWN.value,
        )
        .group_by(StudyAssignment.condition_id)
    ).all()
    return {condition_id: count for condition_id, count in rows}


def choose_condition(
    db: Session, study: Study, participant_code: str
) -> StudyCondition:
    """Pick an arm: least-filled first when balancing, else uniform random."""
    eligible = [c for c in study.conditions if c.is_enabled]
    if not eligible:
        raise NoEligibleConditionError("This study has no enabled conditions.")

    counts = condition_counts(db, study.id)
    rng = _rng_for(study, participant_code)

    if study.max_per_condition is not None:
        eligible = [c for c in eligible if counts.get(c.id, 0) < study.max_per_condition]
        if not eligible:
            raise StudyClosedError(
                "Every condition has reached its participant cap. The study is full."
            )

    if study.balance_conditions:
        lowest = min(counts.get(c.id, 0) for c in eligible)
        candidates = [c for c in eligible if counts.get(c.id, 0) == lowest]
    else:
        candidates = eligible

    # Sort for determinism before the seeded choice, so arm order in the
    # database cannot change the allocation.
    candidates.sort(key=lambda c: (c.order_index, c.id))
    return rng.choice(candidates)


def check_repeat_exposure(db: Session, study: Study, participant_code: str) -> None:
    """Refuse a second explanation of the same concept to the same participant.

    Seeing two explanations of one concept before assessment contaminates both
    measurements, so prior exposure is a hard block rather than a warning.
    """
    existing = db.execute(
        select(StudyAssignment).where(StudyAssignment.participant_code == participant_code)
    ).scalars().all()

    for assignment in existing:
        if assignment.study_id == study.id:
            submitted = db.execute(
                select(ParticipantSubmission).where(
                    ParticipantSubmission.assignment_id == assignment.id
                )
            ).scalar_one_or_none()
            if submitted is not None:
                raise RepeatExposureError(
                    "This participant has already completed this study."
                )
            # Not yet submitted: resume the same arm rather than reassigning.
            return

        other = db.get(Study, assignment.study_id)
        if other is not None and study.question_id and other.question_id == study.question_id:
            raise RepeatExposureError(
                "This participant has already been shown an explanation of this concept "
                "in another study, so their comprehension score would be contaminated."
            )


def item_order_for(study: Study, participant_code: str) -> list[str]:
    """Item order with a methodological constraint.

    Free-text mechanism questions are kept *after* multiple-choice items.
    Writing an explanation is itself a learning intervention (the
    self-explanation effect), so asking it first would change the answers to
    everything after it. Within each block, order is randomised by seed.
    """
    rng = _rng_for(study, participant_code + ":items")
    mcq = [i for i in study.items if i.format == "multiple_choice"]
    free = [i for i in study.items if i.format in {"short_answer", "scenario"}]
    likert = [i for i in study.items if i.format == "likert"]

    for block in (mcq, free, likert):
        block.sort(key=lambda i: i.order_index)
        rng.shuffle(block)

    return [i.id for i in (*mcq, *free, *likert)]


def assign_participant(
    db: Session,
    study: Study,
    *,
    participant_code: str | None = None,
    prior_knowledge: dict | None = None,
    self_reported_level: str | None = None,
) -> StudyAssignment:
    """Create (or resume) an assignment."""
    if study.status != StudyStatus.OPEN.value:
        raise StudyClosedError("This study is not currently accepting participants.")

    code = participant_code or new_participant_code()
    check_repeat_exposure(db, study, code)

    existing = db.execute(
        select(StudyAssignment).where(
            StudyAssignment.study_id == study.id,
            StudyAssignment.participant_code == code,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    condition = choose_condition(db, study, code)
    assignment = StudyAssignment(
        study_id=study.id,
        condition_id=condition.id,
        participant_code=code,
        status=AssignmentStatus.ASSIGNED.value,
        prior_knowledge=prior_knowledge or {},
        self_reported_level=self_reported_level,
        item_order=item_order_for(study, code),
    )
    db.add(assignment)
    db.flush()
    return assignment


def participant_view(
    db: Session, study: Study, assignment: StudyAssignment
) -> dict:
    """Exactly what a participant is allowed to see.

    Built by allow-list. Nothing identifying the model, provider, condition
    label, treatment set or experiment is included — and because this is an
    allow-list, adding a field to the Response model cannot accidentally leak
    one here.
    """
    condition = db.get(StudyCondition, assignment.condition_id)
    response = condition.response
    order = assignment.item_order or [i.id for i in study.items]
    by_id = {i.id: i for i in study.items}
    items = [by_id[i] for i in order if i in by_id]

    return {
        "study": {
            "id": study.id,
            "name": study.name,
            "intro_text": study.intro_text,
            "consent_text": study.consent_text,
            "collect_prior_knowledge": study.collect_prior_knowledge,
        },
        "participant_code": assignment.participant_code,
        "assignment_id": assignment.id,
        # Opaque to the participant; carries no information about the arm.
        "explanation": {"text": response.text},
        "contains_synthetic_stimulus": bool(response.is_synthetic),
        "items": [_participant_item(i) for i in items],
    }


def _participant_item(item: AssessmentItem) -> dict:
    """Item payload with the answer key removed."""
    return {
        "id": item.id,
        "format": item.format,
        "prompt": item.prompt,
        "options": [o.get("text") if isinstance(o, dict) else o for o in (item.options or [])],
        "is_required": item.is_required,
        # dimension is included because the UI groups by it, and it reveals
        # nothing about the condition being tested.
        "dimension": item.dimension,
    }
