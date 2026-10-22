"""Experiment lifecycle and batch execution."""

from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import Response as HTTPResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..enums import ExperimentStatus, JobKind, RunStatus
from ..experiments import orchestrator
from ..experiments.orchestrator import ConfigurationError, ExperimentSpec, ModelRef
from ..jobs import queue
from ..jobs.queue import DuplicateJobError
from ..models import Experiment, ExperimentRun, Job, ResearchReport
from ..reports import exports
from ..schemas import (
    ConditionOut,
    ExperimentOut,
    ExperimentSpecIn,
    JobOut,
    RunOut,
    RunRequest,
)
from ..security import require_researcher

router = APIRouter(dependencies=[Depends(require_researcher)], tags=["experiments"])


def _to_spec(payload: ExperimentSpecIn) -> ExperimentSpec:
    return ExperimentSpec(
        name=payload.name,
        type=payload.type.value,
        question_ids=payload.question_ids,
        source_models=[ModelRef(m.provider.value, m.model_id) for m in payload.source_models],
        prompt_template_keys=payload.prompt_template_keys,
        treatment_sets=payload.treatment_sets,
        transform_models=[
            ModelRef(m.provider.value, m.model_id) for m in payload.transform_models
        ],
        learner_profile_id=payload.learner_profile_id,
        base_prompt_key=payload.base_prompt_key,
        generation_settings=payload.generation_settings.model_dump(exclude_none=True),
        transform_settings=payload.transform_settings.model_dump(exclude_none=True),
        objective=payload.objective,
        hypothesis=payload.hypothesis,
        seed=payload.seed,
        repetitions=payload.repetitions,
        run_analysis=payload.run_analysis,
        run_planning=payload.run_planning,
        run_fidelity=payload.run_fidelity,
        build_concept_graph=payload.build_concept_graph,
        include_untransformed_control=payload.include_untransformed_control,
    )


@router.post("/experiments/estimate")
def estimate_experiment(payload: ExperimentSpecIn, db: Session = Depends(get_db)) -> dict:
    """Pre-flight: how many model calls, and what will it cost?

    Separate from creation so a researcher can see the bill before committing.
    """
    spec = _to_spec(payload)
    try:
        conditions = orchestrator.build_conditions(db, spec)
    except ConfigurationError as exc:
        raise HTTPException(422, str(exc)) from exc
    return orchestrator.estimate(db, spec, conditions)


@router.post("/experiments", response_model=ExperimentOut, status_code=201)
def create_experiment(payload: ExperimentSpecIn, db: Session = Depends(get_db)) -> Experiment:
    spec = _to_spec(payload)
    try:
        experiment, _projection = orchestrator.create_experiment(db, spec)
    except ConfigurationError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return experiment


@router.get("/experiments", response_model=list[ExperimentOut])
def list_experiments(
    db: Session = Depends(get_db),
    status: str | None = None,
    type: str | None = None,
    limit: int = Query(default=100, le=500),
) -> list[Experiment]:
    stmt = select(Experiment).order_by(Experiment.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(Experiment.status == status)
    if type:
        stmt = stmt.where(Experiment.type == type)
    return list(db.execute(stmt).scalars())


def _get_experiment(db: Session, experiment_id: str) -> Experiment:
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(404, "Experiment not found.")
    return experiment


@router.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: str, db: Session = Depends(get_db)) -> dict:
    experiment = _get_experiment(db, experiment_id)
    runs = list(
        db.execute(
            select(ExperimentRun).where(ExperimentRun.experiment_id == experiment_id)
        ).scalars()
    )
    jobs = list(
        db.execute(
            select(Job)
            .where(Job.experiment_id == experiment_id)
            .order_by(Job.created_at.desc())
        ).scalars()
    )
    return {
        "experiment": ExperimentOut.model_validate(experiment).model_dump(),
        "conditions": [
            ConditionOut.model_validate(c).model_dump()
            for c in sorted(experiment.conditions, key=lambda c: c.order_index)
        ],
        "questions": [
            {
                "id": eq.question.id,
                "text": eq.question.text,
                "domain": eq.question.domain,
                "conceptual_difficulty": eq.question.conceptual_difficulty,
            }
            for eq in sorted(experiment.questions, key=lambda q: q.order_index)
        ],
        "runs": [RunOut.model_validate(r).model_dump() for r in runs],
        "run_counts": {
            status: sum(1 for r in runs if r.status == status)
            for status in {r.status for r in runs}
        },
        "jobs": [JobOut.model_validate(j).model_dump() for j in jobs],
    }


@router.post("/experiments/{experiment_id}/run", response_model=JobOut, status_code=202)
def run_experiment(
    experiment_id: str,
    payload: RunRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Job:
    """Queue execution.

    Refuses to start an expensive batch without explicit confirmation, and
    refuses a duplicate submission of the same batch.
    """
    experiment = _get_experiment(db, experiment_id)
    estimate = (experiment.config or {}).get("estimate", {})

    if (
        estimate.get("requires_confirmation")
        and not payload.confirm_cost
        and not settings.demo_mode
    ):
        raise HTTPException(
            409,
            {
                "message": (
                    f"This batch is estimated at ${estimate.get('estimated_cost_usd')} "
                    f"across {estimate.get('total_model_calls')} model calls, above the "
                    f"${estimate.get('confirmation_threshold_usd')} confirmation "
                    "threshold. Re-send with confirm_cost=true to proceed."
                ),
                "estimate": estimate,
                "requires_confirmation": True,
            },
        )

    statuses = (
        [RunStatus.FAILED.value]
        if payload.retry_failed_only
        else [RunStatus.PENDING.value, RunStatus.FAILED.value]
    )
    pending = list(
        db.execute(
            select(ExperimentRun).where(
                ExperimentRun.experiment_id == experiment_id,
                ExperimentRun.status.in_(statuses),
            )
        ).scalars()
    )
    if not pending:
        raise HTTPException(
            409,
            "Nothing to run: every run in this experiment has already succeeded. "
            "Completed records are never regenerated.",
        )

    # Keyed on the exact pending set, so clicking Run twice cannot double-bill,
    # while a genuine later retry of new failures still goes through.
    fingerprint = hashlib.sha256(
        json.dumps(sorted(r.id for r in pending)).encode()
    ).hexdigest()[:32]

    try:
        job = queue.enqueue(
            db,
            kind=JobKind.EXPERIMENT_BATCH,
            payload={
                "experiment_id": experiment_id,
                "retry_failed_only": payload.retry_failed_only,
            },
            experiment_id=experiment_id,
            progress_total=len(pending),
            idempotency_key=f"experiment:{experiment_id}:{fingerprint}",
        )
    except DuplicateJobError as exc:
        raise HTTPException(
            409,
            {
                "message": "This exact batch is already queued or running.",
                "job_id": exc.job.id,
            },
        ) from exc

    experiment.status = ExperimentStatus.RUNNING.value
    db.commit()
    return job


@router.get("/experiments/{experiment_id}/runs", response_model=list[RunOut])
def list_runs(experiment_id: str, db: Session = Depends(get_db)) -> list[ExperimentRun]:
    _get_experiment(db, experiment_id)
    return list(
        db.execute(
            select(ExperimentRun)
            .where(ExperimentRun.experiment_id == experiment_id)
            .order_by(ExperimentRun.created_at)
        ).scalars()
    )


@router.patch("/experiments/{experiment_id}/notes", response_model=ExperimentOut)
def update_notes(
    experiment_id: str, payload: dict, db: Session = Depends(get_db)
) -> Experiment:
    experiment = _get_experiment(db, experiment_id)
    experiment.researcher_notes = str(payload.get("researcher_notes", ""))[:20_000]
    db.commit()
    return experiment


@router.delete("/experiments/{experiment_id}", status_code=204)
def delete_experiment(experiment_id: str, db: Session = Depends(get_db)) -> None:
    experiment = _get_experiment(db, experiment_id)
    db.delete(experiment)
    db.commit()


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}", response_model=JobOut, tags=["jobs"])
def get_job(job_id: str, db: Session = Depends(get_db)) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found.")
    return job


@router.get("/jobs", response_model=list[JobOut], tags=["jobs"])
def list_jobs(
    db: Session = Depends(get_db), limit: int = Query(default=50, le=200)
) -> list[Job]:
    return list(
        db.execute(select(Job).order_by(Job.created_at.desc()).limit(limit)).scalars()
    )


@router.post("/jobs/{job_id}/cancel", response_model=JobOut, tags=["jobs"])
def cancel_job(job_id: str, db: Session = Depends(get_db)) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found.")
    queue.cancel(db, job)
    return job


# ---------------------------------------------------------------------------
# Exports and reports
# ---------------------------------------------------------------------------


@router.get("/experiments/{experiment_id}/export", tags=["exports"])
def export_experiment(
    experiment_id: str,
    format: str = Query(default="json", pattern="^(json|csv|markdown)$"),
    db: Session = Depends(get_db),
):
    experiment = _get_experiment(db, experiment_id)
    if format == "json":
        return exports.experiment_json(db, experiment)

    slug = experiment.name.lower().replace(" ", "-")[:60]
    if format == "csv":
        return HTTPResponse(
            content=exports.experiment_csv(db, experiment),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{slug}.csv"'},
        )
    return HTTPResponse(
        content=exports.experiment_markdown(db, experiment),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{slug}.md"'},
    )


@router.post("/experiments/{experiment_id}/report", status_code=201, tags=["exports"])
def generate_report(experiment_id: str, db: Session = Depends(get_db)) -> dict:
    """Persist a Markdown report and mark the experiment reported."""
    experiment = _get_experiment(db, experiment_id)
    body = exports.experiment_markdown(db, experiment)
    summary = exports.aggregate.experiment_summary(db, experiment)

    report = ResearchReport(
        title=f"{experiment.name} — experiment report",
        kind="experiment",
        experiment_id=experiment.id,
        body_markdown=body,
        data=summary,
        contains_synthetic_data=summary["contains_synthetic_data"],
    )
    db.add(report)
    if experiment.status in {ExperimentStatus.COMPLETED.value, ExperimentStatus.EVALUATED.value}:
        experiment.status = ExperimentStatus.REPORTED.value
    db.commit()
    return {
        "id": report.id,
        "title": report.title,
        "contains_synthetic_data": report.contains_synthetic_data,
        "body_markdown": report.body_markdown,
    }


@router.get("/reports", tags=["exports"])
def list_reports(
    db: Session = Depends(get_db), limit: int = Query(default=50, le=200)
) -> list[dict]:
    reports = list(
        db.execute(
            select(ResearchReport).order_by(ResearchReport.created_at.desc()).limit(limit)
        ).scalars()
    )
    return [
        {
            "id": r.id,
            "title": r.title,
            "kind": r.kind,
            "experiment_id": r.experiment_id,
            "study_id": r.study_id,
            "contains_synthetic_data": r.contains_synthetic_data,
            "created_at": r.created_at.isoformat(),
        }
        for r in reports
    ]


@router.get("/reports/{report_id}", tags=["exports"])
def get_report(report_id: str, db: Session = Depends(get_db)) -> dict:
    report = db.get(ResearchReport, report_id)
    if report is None:
        raise HTTPException(404, "Report not found.")
    return {
        "id": report.id,
        "title": report.title,
        "kind": report.kind,
        "experiment_id": report.experiment_id,
        "study_id": report.study_id,
        "body_markdown": report.body_markdown,
        "data": report.data,
        "contains_synthetic_data": report.contains_synthetic_data,
        "created_at": report.created_at.isoformat(),
    }
