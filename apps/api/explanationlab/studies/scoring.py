"""Scoring participant submissions.

Objective items are scored on submission. Free-text items are left **ungraded**
until a human grades them, or until a researcher explicitly asks for an AI
suggestion — which is stored in a separate column and never becomes the final
score by itself (§6: "Automated grading must not silently replace human
judgments in final research conclusions").
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..enums import AssignmentStatus, EvalDimension, GradingMode, ItemFormat
from ..models import (
    AssessmentItem,
    ItemResponse,
    ParticipantSubmission,
    Study,
    StudyAssignment,
)


@dataclass(slots=True)
class SubmittedAnswer:
    item_id: str
    selected_option_index: int | None = None
    text_answer: str = ""
    likert_value: int | None = None
    seconds_spent: float | None = None


def score_objective(item: AssessmentItem, answer: SubmittedAnswer) -> tuple[float | None, bool]:
    """Return (score, misconception_detected) for an auto-scorable item."""
    if item.format != ItemFormat.MULTIPLE_CHOICE.value:
        return None, False
    if answer.selected_option_index is None or item.correct_option_index is None:
        return None, False

    correct = answer.selected_option_index == item.correct_option_index
    score = item.max_score if correct else 0.0
    # A distractor can be tagged as diagnostic of a specific misconception.
    misconception = (
        not correct and answer.selected_option_index in (item.misconception_option_indexes or [])
    )
    return score, misconception


def record_submission(
    db: Session,
    study: Study,
    assignment: StudyAssignment,
    *,
    answers: list[SubmittedAnswer],
    reading_seconds: float | None,
    assessment_seconds: float | None,
    clarity_rating: int | None,
    cognitive_effort_rating: int | None,
    free_text_feedback: str = "",
) -> ParticipantSubmission:
    """Persist one participant's submission with scores where determinable."""
    submission = ParticipantSubmission(
        assignment_id=assignment.id,
        reading_seconds=reading_seconds,
        assessment_seconds=assessment_seconds,
        clarity_rating=_clamp_likert(clarity_rating),
        cognitive_effort_rating=_clamp_likert(cognitive_effort_rating),
        free_text_feedback=free_text_feedback[:5000],
    )
    db.add(submission)
    db.flush()

    items_by_id = {i.id: i for i in study.items}
    order = assignment.item_order or list(items_by_id)

    for answer in answers:
        item = items_by_id.get(answer.item_id)
        if item is None:
            continue  # ignore answers to items not in this study
        score, misconception = score_objective(item, answer)
        db.add(
            ItemResponse(
                submission_id=submission.id,
                item_id=item.id,
                selected_option_index=answer.selected_option_index,
                text_answer=(answer.text_answer or "")[:8000],
                likert_value=_clamp_likert(answer.likert_value),
                seconds_spent=answer.seconds_spent,
                presented_order=order.index(item.id) if item.id in order else 0,
                auto_score=score,
                grading_mode=(
                    GradingMode.AUTO_OBJECTIVE.value
                    if score is not None
                    else GradingMode.MANUAL.value
                ),
                misconception_detected=misconception,
            )
        )

    assignment.status = AssignmentStatus.SUBMITTED.value
    db.flush()
    return submission


def _clamp_likert(value: int | None) -> int | None:
    if value is None:
        return None
    try:
        return max(1, min(7, int(value)))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Per-submission summary
# ---------------------------------------------------------------------------

_COMPREHENSION_DIMENSIONS = {
    EvalDimension.IMMEDIATE_COMPREHENSION.value,
    EvalDimension.MECHANISTIC_UNDERSTANDING.value,
    EvalDimension.TRANSFER.value,
}


def summarise_submission(db: Session, submission: ParticipantSubmission) -> dict:
    """Per-dimension summary. Dimensions stay separate on purpose."""
    by_dimension: dict[str, dict] = {}
    pending_grading = 0

    for ir in submission.item_responses:
        item = ir.item
        bucket = by_dimension.setdefault(
            item.dimension,
            {"earned": 0.0, "available": 0.0, "graded_items": 0, "ungraded_items": 0},
        )
        score = ir.final_score
        bucket["available"] += item.max_score
        if score is None:
            bucket["ungraded_items"] += 1
            pending_grading += 1
        else:
            bucket["earned"] += score
            bucket["graded_items"] += 1

    for bucket in by_dimension.values():
        bucket["score_ratio"] = (
            round(bucket["earned"] / bucket["available"], 4) if bucket["available"] else None
        )
        # Partial grading makes a ratio misleading, so flag it explicitly.
        bucket["complete"] = bucket["ungraded_items"] == 0

    comprehension = {
        k: v for k, v in by_dimension.items() if k in _COMPREHENSION_DIMENSIONS
    }
    earned = sum(v["earned"] for v in comprehension.values())
    available = sum(v["available"] for v in comprehension.values())

    return {
        "submission_id": submission.id,
        "participant_code": submission.assignment.participant_code,
        "condition_id": submission.assignment.condition_id,
        "by_dimension": by_dimension,
        "comprehension_score": round(earned / available, 4) if available else None,
        "comprehension_complete": all(v["complete"] for v in comprehension.values())
        if comprehension
        else False,
        "pending_grading_items": pending_grading,
        "misconception_count": sum(
            1 for ir in submission.item_responses if ir.misconception_detected
        ),
        # Reported separately from comprehension, never averaged with it.
        "perceived_clarity": submission.clarity_rating,
        "cognitive_effort": submission.cognitive_effort_rating,
        "reading_seconds": submission.reading_seconds,
        "assessment_seconds": submission.assessment_seconds,
    }
