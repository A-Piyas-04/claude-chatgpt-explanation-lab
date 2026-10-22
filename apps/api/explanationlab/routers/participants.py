"""Participant-facing endpoints. **Public** — authenticated only by study token.

Security properties of this router:

- It has **no** researcher dependency, so a leaked study token cannot reach
  researcher controls, experiment configuration, or any other study.
- Every payload is assembled by the allow-list in
  :func:`explanationlab.studies.assignment.participant_view`, so model identity,
  condition labels, treatment names and answer keys cannot leak by accident.
- Withdrawal deletes the participant's submitted answers, rather than flagging
  them, because that is what "permit participants to withdraw" should mean.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..enums import AssignmentStatus, StudyStatus
from ..models import ParticipantSubmission, Study, StudyAssignment, utcnow
from ..schemas import ParticipantEnter, ParticipantSubmit
from ..studies import assignment as assignment_service
from ..studies.assignment import (
    NoEligibleConditionError,
    RepeatExposureError,
    StudyClosedError,
)
from ..studies.scoring import SubmittedAnswer, record_submission

router = APIRouter(prefix="/p", tags=["participants"])


def _study_by_token(db: Session, token: str) -> Study:
    study = db.execute(
        select(Study).where(Study.access_token == token)
    ).scalar_one_or_none()
    if study is None:
        # Deliberately indistinguishable from a closed study, so the endpoint
        # cannot be used to confirm whether a token exists.
        raise HTTPException(404, "This study link is not valid.")
    return study


@router.get("/{token}")
def study_intro(token: str, db: Session = Depends(get_db)) -> dict:
    """Consent screen. No explanation text until consent is given."""
    study = _study_by_token(db, token)
    if study.status != StudyStatus.OPEN.value:
        raise HTTPException(403, "This study is not currently accepting participants.")

    return {
        "study_name": study.name,
        "intro_text": study.intro_text,
        "consent_text": study.consent_text,
        "collect_prior_knowledge": study.collect_prior_knowledge,
        "estimated_minutes": max(5, 2 + len(study.items)),
        "item_count": len(study.items),
    }


@router.post("/{token}/enter", status_code=201)
def enter_study(
    token: str, payload: ParticipantEnter, db: Session = Depends(get_db)
) -> dict:
    """Consent, get assigned to a blinded condition, and receive the stimulus."""
    study = _study_by_token(db, token)

    try:
        assignment = assignment_service.assign_participant(
            db,
            study,
            participant_code=payload.participant_code,
            prior_knowledge=payload.prior_knowledge,
            self_reported_level=(
                payload.self_reported_level.value if payload.self_reported_level else None
            ),
        )
    except RepeatExposureError as exc:
        raise HTTPException(409, str(exc)) from exc
    except StudyClosedError as exc:
        raise HTTPException(403, str(exc)) from exc
    except NoEligibleConditionError as exc:
        raise HTTPException(503, str(exc)) from exc

    if assignment.status == AssignmentStatus.SUBMITTED.value:
        raise HTTPException(409, "You have already completed this study. Thank you.")

    assignment.consented_at = assignment.consented_at or utcnow()
    assignment.status = AssignmentStatus.CONSENTED.value
    db.commit()

    return assignment_service.participant_view(db, study, assignment)


@router.post("/{token}/submit", status_code=201)
def submit_assessment(
    token: str, payload: ParticipantSubmit, db: Session = Depends(get_db)
) -> dict:
    study = _study_by_token(db, token)
    assignment = db.execute(
        select(StudyAssignment).where(
            StudyAssignment.study_id == study.id,
            StudyAssignment.participant_code == payload.participant_code,
        )
    ).scalar_one_or_none()
    if assignment is None:
        raise HTTPException(404, "No active session found for this participant code.")
    if assignment.withdrawn_at is not None:
        raise HTTPException(409, "This participant has withdrawn from the study.")

    existing = db.execute(
        select(ParticipantSubmission).where(
            ParticipantSubmission.assignment_id == assignment.id
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(409, "An assessment has already been submitted for this session.")

    required = {i.id for i in study.items if i.is_required}
    answered = {
        a.item_id
        for a in payload.answers
        if a.selected_option_index is not None
        or a.text_answer.strip()
        or a.likert_value is not None
    }
    if required - answered:
        raise HTTPException(
            422,
            {
                "message": "Some required questions have not been answered.",
                "unanswered_item_ids": sorted(required - answered),
            },
        )

    record_submission(
        db,
        study,
        assignment,
        answers=[
            SubmittedAnswer(
                item_id=a.item_id,
                selected_option_index=a.selected_option_index,
                text_answer=a.text_answer,
                likert_value=a.likert_value,
                seconds_spent=a.seconds_spent,
            )
            for a in payload.answers
        ],
        reading_seconds=payload.reading_seconds,
        assessment_seconds=payload.assessment_seconds,
        clarity_rating=payload.clarity_rating,
        cognitive_effort_rating=payload.cognitive_effort_rating,
        free_text_feedback=payload.free_text_feedback,
    )
    db.commit()

    # No score is returned: telling participants how they did would make a
    # delayed-retention follow-up uninterpretable, and invites them to compare
    # notes with other participants.
    return {
        "status": "submitted",
        "participant_code": payload.participant_code,
        "message": (
            "Thank you. Your responses have been recorded. Results are reported only "
            "in aggregate, never individually."
        ),
        "withdraw_path": f"/p/{token}/withdraw",
    }


@router.post("/{token}/withdraw")
def withdraw(token: str, payload: dict, db: Session = Depends(get_db)) -> dict:
    """Withdraw and delete this participant's data."""
    study = _study_by_token(db, token)
    code = str(payload.get("participant_code", ""))[:32]
    assignment = db.execute(
        select(StudyAssignment).where(
            StudyAssignment.study_id == study.id,
            StudyAssignment.participant_code == code,
        )
    ).scalar_one_or_none()
    if assignment is None:
        raise HTTPException(404, "No session found for this participant code.")

    submission = db.execute(
        select(ParticipantSubmission).where(
            ParticipantSubmission.assignment_id == assignment.id
        )
    ).scalar_one_or_none()
    if submission is not None:
        # Cascades to item_responses.
        db.delete(submission)

    assignment.withdrawn_at = utcnow()
    assignment.status = AssignmentStatus.WITHDRAWN.value
    assignment.prior_knowledge = {}
    db.commit()

    return {
        "status": "withdrawn",
        "message": "Your responses have been deleted. Thank you for your time.",
    }
