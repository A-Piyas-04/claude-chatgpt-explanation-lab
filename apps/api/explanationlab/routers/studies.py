"""Researcher-side human study management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import Response as HTTPResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..analytics import aggregate
from ..db import get_db
from ..enums import GradingMode, ItemFormat, StudyStatus
from ..evaluation.judge import grade_short_answer
from ..evaluation.proxy import evaluate_study
from ..models import (
    AssessmentItem,
    GradingRubric,
    ItemResponse,
    ParticipantSubmission,
    ResearchQuestion,
    ResearchReport,
    Response,
    Study,
    StudyAssignment,
    StudyCondition,
)
from ..providers.base import ProviderError
from ..reports import exports
from ..schemas import GradeIn, ProxyRunIn, StudyCreate, StudyOut
from ..security import new_study_token, require_researcher
from ..studies.scoring import summarise_submission

router = APIRouter(dependencies=[Depends(require_researcher)], tags=["studies"])

DEFAULT_CONSENT = """\
**What this is.** A short reading-and-comprehension exercise for research into how
understandable AI-generated explanations are.

**What you will do.** Read one explanation, then answer a few questions about it.
It should take about 10 minutes.

**What we record.** Your answers, how long you spent, and your ratings. You are
identified only by a random code. We do not ask for your name, email, or any
other personal information, and we do not collect your IP address.

**Your choices.** You may stop at any time without giving a reason, and you may
withdraw your data using the button on the page. Individual results are never
published; only aggregates are reported.

**Blinding.** You will not be told which system produced the explanation you
read, because knowing would change how you rate it.
"""


def _get_study(db: Session, study_id: str) -> Study:
    study = db.get(Study, study_id)
    if study is None:
        raise HTTPException(404, "Study not found.")
    return study


@router.post("/studies", response_model=StudyOut, status_code=201)
def create_study(payload: StudyCreate, db: Session = Depends(get_db)) -> Study:
    responses = list(
        db.execute(select(Response).where(Response.id.in_(payload.response_ids))).scalars()
    )
    if len(responses) != len(set(payload.response_ids)):
        missing = set(payload.response_ids) - {r.id for r in responses}
        raise HTTPException(404, f"Unknown response ids: {sorted(missing)}")

    # Comparing explanations of different questions would confound the
    # comparison with question difficulty, so refuse it outright.
    question_ids = {r.question_id for r in responses if r.question_id}
    if len(question_ids) > 1:
        raise HTTPException(
            422,
            "All conditions in one study must answer the same research question. "
            "Otherwise differences between arms are confounded with question difficulty.",
        )

    study = Study(
        name=payload.name,
        status=StudyStatus.DRAFT.value,
        question_id=payload.question_id or (next(iter(question_ids)) if question_ids else None),
        experiment_id=payload.experiment_id,
        intro_text=payload.intro_text
        or "Please read the explanation below carefully, then answer the questions.",
        consent_text=payload.consent_text or DEFAULT_CONSENT,
        collect_prior_knowledge=payload.collect_prior_knowledge,
        seed=payload.seed,
        balance_conditions=payload.balance_conditions,
        max_per_condition=payload.max_per_condition,
        access_token=new_study_token(),
    )
    db.add(study)
    db.flush()

    by_id = {r.id: r for r in responses}
    for index, response_id in enumerate(payload.response_ids):
        response = by_id[response_id]
        treatments = "+".join(response.applied_treatments or []) or "untransformed"
        condition_label = (
            response.label[:200]
            if response.origin == "manual_import" and response.label
            else f"{response.provider}/{response.model_id} [{treatments}]"[:200]
        )
        db.add(
            StudyCondition(
                study_id=study.id,
                # Researcher-facing label; never leaves the researcher API.
                label=condition_label,
                response_id=response.id,
                order_index=index,
            )
        )

    for index, item in enumerate(payload.items):
        rubric_id = None
        if item.rubric_key:
            rubric = db.execute(
                select(GradingRubric)
                .where(GradingRubric.key == item.rubric_key)
                .order_by(GradingRubric.version.desc())
            ).scalars().first()
            rubric_id = rubric.id if rubric else None
        db.add(
            AssessmentItem(
                study_id=study.id,
                order_index=index,
                format=item.format.value,
                dimension=item.dimension.value,
                prompt=item.prompt,
                options=[{"text": o} for o in item.options],
                correct_option_index=item.correct_option_index,
                misconception_option_indexes=item.misconception_option_indexes,
                rubric_id=rubric_id,
                max_score=item.max_score,
                is_required=item.is_required,
            )
        )

    db.commit()
    return study


@router.get("/studies", response_model=list[StudyOut])
def list_studies(
    db: Session = Depends(get_db), limit: int = Query(default=100, le=500)
) -> list[Study]:
    return list(
        db.execute(select(Study).order_by(Study.created_at.desc()).limit(limit)).scalars()
    )


@router.get("/studies/{study_id}")
def get_study(study_id: str, db: Session = Depends(get_db)) -> dict:
    study = _get_study(db, study_id)
    assignments = list(
        db.execute(
            select(StudyAssignment).where(StudyAssignment.study_id == study_id)
        ).scalars()
    )
    return {
        "study": StudyOut.model_validate(study).model_dump(),
        "participant_url_path": f"/p/{study.access_token}",
        "conditions": [
            {
                "id": c.id,
                "label": c.label,
                "response_id": c.response_id,
                "model_id": c.response.model_id,
                "provider": c.response.provider,
                "treatments": c.response.applied_treatments,
                "is_enabled": c.is_enabled,
                "is_synthetic": c.response.is_synthetic,
                "assigned": sum(1 for a in assignments if a.condition_id == c.id),
            }
            for c in sorted(study.conditions, key=lambda c: c.order_index)
        ],
        "items": [
            {
                "id": i.id,
                "order_index": i.order_index,
                "format": i.format,
                "dimension": i.dimension,
                "prompt": i.prompt,
                "options": [o.get("text") for o in (i.options or [])],
                "correct_option_index": i.correct_option_index,
                "misconception_option_indexes": i.misconception_option_indexes,
                "max_score": i.max_score,
                "rubric_id": i.rubric_id,
            }
            for i in study.items
        ],
        "participants": {
            "assigned": len(assignments),
            "submitted": sum(1 for a in assignments if a.status == "submitted"),
            "withdrawn": sum(1 for a in assignments if a.withdrawn_at is not None),
        },
    }


@router.post("/studies/{study_id}/status", response_model=StudyOut)
def set_status(study_id: str, payload: dict, db: Session = Depends(get_db)) -> Study:
    study = _get_study(db, study_id)
    target = payload.get("status")
    if target not in {s.value for s in StudyStatus}:
        raise HTTPException(422, f"Unknown status '{target}'.")
    if target == StudyStatus.OPEN.value:
        if len([c for c in study.conditions if c.is_enabled]) < 2:
            raise HTTPException(422, "A study needs at least two enabled conditions.")
        if not study.items:
            raise HTTPException(422, "A study needs at least one assessment item.")
    study.status = target
    db.commit()
    return study


@router.post("/studies/{study_id}/rotate-token", response_model=StudyOut)
def rotate_token(study_id: str, db: Session = Depends(get_db)) -> Study:
    """Invalidate the participant link (e.g. if it leaked)."""
    study = _get_study(db, study_id)
    study.access_token = new_study_token()
    db.commit()
    return study


@router.get("/studies/{study_id}/results")
def study_results(study_id: str, db: Session = Depends(get_db)) -> dict:
    return aggregate.study_results(db, _get_study(db, study_id))


@router.post("/studies/{study_id}/proxy-evaluation", status_code=201)
def run_proxy_evaluation(
    study_id: str, payload: ProxyRunIn, db: Session = Depends(get_db)
) -> dict:
    """Audit answerability with a live model; never create participant records."""
    study = _get_study(db, study_id)
    try:
        result = evaluate_study(
            db, study, provider=payload.provider.value, model_id=payload.model_id
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except ProviderError as exc:
        db.commit()  # preserve model usage and error records
        raise HTTPException(502, {"message": str(exc), "error_type": exc.error_type}) from exc

    body = (
        f"# AI proxy answerability audit — {study.name}\n\n"
        f"Model: {payload.provider.value}/{payload.model_id}\n\n"
        f"No-explanation baseline: {result['baseline_correct_count']}/{result['item_count']} "
        "items already answered correctly.\n\n"
        f"Diagnostic items: {result['diagnostic_item_count']}.\n\n"
        + "\n".join(
            f"- {condition['label']}: {condition['grounded_correct']}/{result['item_count']} "
            "answers correct with a quote found in the text; "
            f"{condition['diagnostic_grounded_correct']}/{result['diagnostic_item_count']} "
            "on diagnostic items."
            for condition in result["conditions"]
        )
        + f"\n\n**Limit:** {result['warning']}\n"
    )
    report = ResearchReport(
        title=f"{study.name} — AI proxy audit",
        kind="ai_proxy_answerability",
        study_id=study.id,
        body_markdown=body,
        data=result,
        contains_synthetic_data=False,
    )
    db.add(report)
    db.commit()
    return {"id": report.id, **result}


@router.get("/studies/{study_id}/proxy-evaluation")
def latest_proxy_evaluation(study_id: str, db: Session = Depends(get_db)) -> dict | None:
    _get_study(db, study_id)
    report = db.execute(
        select(ResearchReport)
        .where(ResearchReport.study_id == study_id)
        .where(ResearchReport.kind == "ai_proxy_answerability")
        .order_by(ResearchReport.created_at.desc(), ResearchReport.id.desc())
    ).scalars().first()
    return {"id": report.id, **report.data} if report else None


@router.get("/studies/{study_id}/comparison")
def study_comparison(study_id: str, db: Session = Depends(get_db)) -> dict:
    return aggregate.condition_comparison(db, _get_study(db, study_id))


@router.get("/studies/{study_id}/submissions")
def list_submissions(study_id: str, db: Session = Depends(get_db)) -> list[dict]:
    """Anonymised submissions with their items, for grading."""
    study = _get_study(db, study_id)
    assignment_ids = [
        a.id
        for a in db.execute(
            select(StudyAssignment).where(StudyAssignment.study_id == study_id)
        ).scalars()
    ]
    submissions = list(
        db.execute(
            select(ParticipantSubmission).where(
                ParticipantSubmission.assignment_id.in_(assignment_ids or [""])
            )
        ).scalars()
    )
    conditions = {c.id: c for c in study.conditions}

    out = []
    for submission in submissions:
        summary = summarise_submission(db, submission)
        condition = conditions.get(submission.assignment.condition_id)
        out.append(
            {
                "summary": summary,
                "condition_label": condition.label if condition else "",
                "items": [
                    {
                        "item_response_id": ir.id,
                        "item_id": ir.item_id,
                        "format": ir.item.format,
                        "dimension": ir.item.dimension,
                        "prompt": ir.item.prompt,
                        "max_score": ir.item.max_score,
                        "selected_option_index": ir.selected_option_index,
                        "text_answer": ir.text_answer,
                        "likert_value": ir.likert_value,
                        "auto_score": ir.auto_score,
                        "ai_suggested_score": ir.ai_suggested_score,
                        "ai_rationale": ir.ai_rationale,
                        "human_score": ir.human_score,
                        "final_score": ir.final_score,
                        "grading_mode": ir.grading_mode,
                        "misconception_detected": ir.misconception_detected,
                        "grader_notes": ir.grader_notes,
                        "needs_grading": ir.final_score is None,
                    }
                    for ir in submission.item_responses
                ],
            }
        )
    return out


@router.post("/item-responses/{item_response_id}/grade")
def grade_item(
    item_response_id: str, payload: GradeIn, db: Session = Depends(get_db)
) -> dict:
    """Record a human grade. This is the authoritative score."""
    item_response = db.get(ItemResponse, item_response_id)
    if item_response is None:
        raise HTTPException(404, "Item response not found.")
    if payload.human_score > item_response.item.max_score:
        raise HTTPException(
            422,
            f"Score exceeds this item's maximum of {item_response.item.max_score}.",
        )
    item_response.human_score = payload.human_score
    item_response.misconception_detected = payload.misconception_detected
    item_response.grader_notes = payload.grader_notes
    item_response.grading_mode = GradingMode.MANUAL.value
    db.commit()
    return {
        "id": item_response.id,
        "human_score": item_response.human_score,
        "final_score": item_response.final_score,
    }


@router.post("/studies/{study_id}/ai-grade")
def ai_grade(
    study_id: str,
    provider: str = Query(...),
    model_id: str = Query(...),
    effort: str | None = None,
    overwrite: bool = False,
    db: Session = Depends(get_db),
) -> dict:
    """Produce AI grading *suggestions* for ungraded free-text answers.

    Suggestions land in ``ai_suggested_score`` and never in ``human_score``, so
    they cannot become the final figure without a human acting on them.
    """
    study = _get_study(db, study_id)
    assignment_ids = [
        a.id
        for a in db.execute(
            select(StudyAssignment).where(StudyAssignment.study_id == study_id)
        ).scalars()
    ]
    submissions = list(
        db.execute(
            select(ParticipantSubmission).where(
                ParticipantSubmission.assignment_id.in_(assignment_ids or [""])
            )
        ).scalars()
    )

    question = db.get(ResearchQuestion, study.question_id) if study.question_id else None
    checklist = list(question.factual_checklist or []) if question else []

    graded = 0
    skipped = 0
    total_cost = 0.0
    errors: list[str] = []

    free_formats = {ItemFormat.SHORT_ANSWER.value, ItemFormat.SCENARIO.value}
    for submission in submissions:
        for ir in submission.item_responses:
            if ir.item.format not in free_formats:
                continue
            if ir.human_score is not None and not overwrite:
                skipped += 1
                continue
            if ir.ai_suggested_score is not None and not overwrite:
                skipped += 1
                continue
            if not ir.text_answer.strip():
                skipped += 1
                continue

            rubric = ir.item.rubric
            rubric_payload = (
                {"criteria": rubric.criteria, "max_score": rubric.max_score}
                if rubric
                else {"criteria": [], "max_score": ir.item.max_score}
            )
            try:
                grade, cost = grade_short_answer(
                    db,
                    provider=provider,
                    model_id=model_id,
                    question_prompt=ir.item.prompt,
                    learner_answer=ir.text_answer,
                    rubric=rubric_payload,
                    reference_claims=checklist,
                    effort=effort,
                )
            except ProviderError as exc:
                errors.append(f"{ir.id}: {exc}")
                continue

            ir.ai_suggested_score = grade["score"]
            ir.ai_rationale = (
                f"[{grade['grader']}] {grade['rationale']}"
                + (
                    f"\nPossible misconception: {grade['misconception_detail']}"
                    if grade["misconception_detected"]
                    else ""
                )
            )
            ir.rubric_version = rubric.version if rubric else None
            ir.grading_mode = GradingMode.AI_ASSISTED.value
            graded += 1
            total_cost += cost

    db.commit()
    return {
        "ai_suggestions_created": graded,
        "skipped": skipped,
        "errors": errors,
        "estimated_cost_usd": round(total_cost, 6),
        "note": (
            "These are suggestions stored separately from human scores. Aggregate "
            "comprehension figures use human scores and objective auto-scores only; "
            "a suggestion must be confirmed by a grader to count."
        ),
    }


@router.get("/studies/{study_id}/export")
def export_study(
    study_id: str,
    format: str = Query(default="csv", pattern="^(csv|markdown|json)$"),
    db: Session = Depends(get_db),
):
    study = _get_study(db, study_id)
    slug = study.name.lower().replace(" ", "-")[:60]
    if format == "csv":
        return HTTPResponse(
            content=exports.study_csv(db, study),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{slug}.csv"'},
        )
    if format == "markdown":
        return HTTPResponse(
            content=exports.study_markdown(db, study),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{slug}.md"'},
        )
    return aggregate.study_results(db, study)


@router.post("/studies/{study_id}/report", status_code=201)
def generate_study_report(study_id: str, db: Session = Depends(get_db)) -> dict:
    study = _get_study(db, study_id)
    results = aggregate.study_results(db, study)
    report = ResearchReport(
        title=f"{study.name} — human comprehension study report",
        kind="human_study",
        study_id=study.id,
        body_markdown=exports.study_markdown(db, study),
        data=results,
        contains_synthetic_data=results["contains_synthetic_data"],
    )
    db.add(report)
    db.commit()
    return {
        "id": report.id,
        "title": report.title,
        "body_markdown": report.body_markdown,
        "contains_synthetic_data": report.contains_synthetic_data,
    }
