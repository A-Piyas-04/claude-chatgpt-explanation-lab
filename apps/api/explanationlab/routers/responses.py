"""Responses: comparison, manual import, ad-hoc transformation, judging, graphs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..concepts import graph as graph_utils
from ..db import get_db
from ..enums import JobKind, ResponseKind, ResponseOrigin
from ..evaluation.judge import judge_response
from ..evaluation.metrics import compute_metrics
from ..jobs import queue
from ..models import (
    Annotation,
    ConceptGraph,
    FidelityReport,
    JudgeEvaluation,
    ResearchQuestion,
    Response,
    TextMetrics,
)
from ..providers.base import ProviderError
from ..schemas import (
    AnnotationCreate,
    JudgeRequest,
    ResponseImport,
    ResponseOut,
    TransformRequest,
)
from ..security import require_researcher
from ..transformations.pipeline import (
    LearnerContext,
    PipelineConfig,
    TransformationPipeline,
)

router = APIRouter(dependencies=[Depends(require_researcher)], tags=["responses"])


def _get_response(db: Session, response_id: str) -> Response:
    response = db.get(Response, response_id)
    if response is None:
        raise HTTPException(404, "Response not found.")
    return response


@router.get("/responses", response_model=list[ResponseOut])
def list_responses(
    db: Session = Depends(get_db),
    question_id: str | None = None,
    experiment_id: str | None = None,
    kind: str | None = None,
    provider: str | None = None,
    include_synthetic: bool = True,
    limit: int = Query(default=200, le=1000),
) -> list[Response]:
    stmt = select(Response).order_by(Response.created_at.desc()).limit(limit)
    if question_id:
        stmt = stmt.where(Response.question_id == question_id)
    if kind:
        stmt = stmt.where(Response.kind == kind)
    if provider:
        stmt = stmt.where(Response.provider == provider)
    if not include_synthetic:
        stmt = stmt.where(Response.is_synthetic.is_(False))

    results = list(db.execute(stmt).scalars())
    if experiment_id:
        results = [
            r for r in results if r.run is not None and r.run.experiment_id == experiment_id
        ]
    return results


@router.get("/responses/{response_id}")
def get_response_detail(response_id: str, db: Session = Depends(get_db)) -> dict:
    """Everything the comparison and analysis workspaces need for one response."""
    response = _get_response(db, response_id)
    metrics = db.execute(
        select(TextMetrics).where(TextMetrics.response_id == response_id)
    ).scalar_one_or_none()
    judges = list(
        db.execute(
            select(JudgeEvaluation).where(JudgeEvaluation.response_id == response_id)
        ).scalars()
    )
    fidelity = list(
        db.execute(
            select(FidelityReport).where(FidelityReport.response_id == response_id)
        ).scalars()
    )
    graphs = list(
        db.execute(
            select(ConceptGraph).where(ConceptGraph.response_id == response_id)
        ).scalars()
    )
    annotations = list(
        db.execute(select(Annotation).where(Annotation.response_id == response_id)).scalars()
    )
    parent = db.get(Response, response.parent_response_id) if response.parent_response_id else None

    return {
        "response": ResponseOut.model_validate(response).model_dump(),
        "question": (
            {
                "id": response.question.id,
                "text": response.question.text,
                "domain": response.question.domain,
                "factual_checklist": response.question.factual_checklist,
            }
            if response.question
            else None
        ),
        "learner_profile": (
            {
                "id": response.learner_profile.id,
                "name": response.learner_profile.name,
                "level": response.learner_profile.level,
            }
            if response.learner_profile
            else None
        ),
        "source_response": (
            {"id": parent.id, "text": parent.text, "model_id": parent.model_id}
            if parent
            else None
        ),
        "transformation_meta": response.transformation_meta,
        "automated_diagnostics": {
            "evidence_class": "automated_diagnostic",
            "metrics": metrics.metrics if metrics else None,
        },
        "ai_judge_evaluations": [
            {
                "id": j.id,
                "provider": j.provider,
                "model_id": j.model_id,
                "rubric": f"{j.rubric_key} v{j.rubric_version}",
                "blinded": j.blinded,
                "scores": j.scores,
                "overall_notes": j.overall_notes,
                "is_synthetic": j.is_synthetic,
                "evidence_class": "ai_judge_opinion",
                "created_at": j.created_at.isoformat(),
            }
            for j in judges
        ],
        "fidelity_reports": [
            {
                "id": f.id,
                "verdict": f.verdict,
                "warnings": f.warnings,
                "numeric_drift": f.numeric_drift,
                "checklist_coverage": f.checklist_coverage,
                "reviewed_by_human": f.reviewed_by_human,
                "provisional": True,
            }
            for f in fidelity
        ],
        "concept_graphs": [
            {
                "id": g.id,
                "nodes": g.nodes,
                "edges": g.edges,
                "teaching_order": g.teaching_order,
                "cycles_detected": g.cycles_detected,
                "model_id": g.model_id,
                "is_hypothesis": True,
                "is_synthetic": g.is_synthetic,
            }
            for g in graphs
        ],
        "annotations": [
            {
                "id": a.id,
                "author": a.author,
                "label": a.label,
                "body": a.body,
                "quoted_excerpt": a.quoted_excerpt,
                "created_at": a.created_at.isoformat(),
            }
            for a in annotations
        ],
    }


@router.post("/responses/import", response_model=ResponseOut, status_code=201)
def import_response(payload: ResponseImport, db: Session = Depends(get_db)) -> Response:
    """Paste a real answer from a consumer chat interface.

    This exists because API output and the ChatGPT/Claude consumer interfaces are
    not the same system, and the brief is explicit that we must not assume they
    are. Provenance records the difference instead of hiding it.
    """
    question = db.get(ResearchQuestion, payload.question_id)
    if question is None:
        raise HTTPException(404, "Research question not found.")

    response = Response(
        kind=ResponseKind.SOURCE.value,
        origin=ResponseOrigin.MANUAL_IMPORT.value,
        question_id=question.id,
        learner_profile_id=payload.learner_profile_id,
        provider=payload.provider.value,
        model_id=payload.model_id,
        label=payload.label or f"Manual import — {payload.provider.value}/{payload.model_id}",
        system_prompt_snapshot="(unknown: captured from a consumer interface)",
        user_prompt_snapshot=question.text,
        generation_settings={},
        requested_settings={},
        control_limitations=[
            f"Manually imported from a {payload.interface} interface. Generation "
            "settings, system prompt and any product-side scaffolding are unknown "
            "and are NOT comparable to API conditions.",
            f"Captured at: {payload.captured_at.isoformat() if payload.captured_at else 'not recorded'}",
        ],
        text=payload.text,
        is_synthetic=False,
    )
    db.add(response)
    db.flush()

    metrics = compute_metrics(
        response.text, factual_checklist=list(question.factual_checklist or [])
    )
    db.add(TextMetrics(response_id=response.id, metrics=metrics))
    if payload.notes:
        db.add(
            Annotation(
                response_id=response.id, label="import note", body=payload.notes
            )
        )
    db.commit()
    return response


@router.post("/responses/{response_id}/annotations", status_code=201)
def add_annotation(
    response_id: str, payload: AnnotationCreate, db: Session = Depends(get_db)
) -> dict:
    _get_response(db, response_id)
    annotation = Annotation(response_id=response_id, **payload.model_dump())
    db.add(annotation)
    db.commit()
    return {"id": annotation.id, "created_at": annotation.created_at.isoformat()}


@router.post("/responses/{response_id}/metrics")
def recompute_metrics(response_id: str, db: Session = Depends(get_db)) -> dict:
    """Recompute diagnostics without re-calling any model."""
    response = _get_response(db, response_id)
    metrics = compute_metrics(
        response.text,
        factual_checklist=list(response.question.factual_checklist or [])
        if response.question
        else [],
    )
    db.merge(TextMetrics(response_id=response.id, metrics=metrics))
    db.commit()
    return {"evidence_class": "automated_diagnostic", "metrics": metrics}


@router.post("/responses/{response_id}/transform", status_code=201)
def transform_response(
    response_id: str, payload: TransformRequest, db: Session = Depends(get_db)
) -> dict:
    """Run the transformation pipeline on one response (Transformation Workbench)."""
    source = _get_response(db, response_id)
    profile = source.learner_profile
    question = source.question

    learner = LearnerContext(
        level=profile.level if profile else "unspecified",
        description=profile.description if profile else "",
        assumed_prior_knowledge=", ".join(profile.assumed_prior_knowledge or [])
        if profile
        else "unspecified",
        unfamiliar_with=", ".join(profile.unfamiliar_with or []) if profile else "unspecified",
    )
    settings = payload.settings.model_dump(exclude_none=True)

    pipeline = TransformationPipeline(db)
    try:
        result = pipeline.run(
            source_text=source.text,
            question_text=question.text if question else "",
            learner=learner,
            config=PipelineConfig(
                treatments=payload.treatments,
                provider=payload.provider.value,
                model_id=payload.model_id,
                effort=settings.get("effort"),
                temperature=settings.get("temperature"),
                max_output_tokens=int(settings.get("max_output_tokens", 6000)),
                run_analysis=payload.run_analysis,
                run_planning=payload.run_planning,
                run_fidelity=payload.run_fidelity,
                factual_checklist=list(question.factual_checklist or []) if question else [],
                treatment_order_override=payload.treatment_order_override,
            ),
        )
    except ProviderError as exc:
        db.commit()  # keep the usage/error records
        raise HTTPException(502, {"message": str(exc), "error_type": exc.error_type}) from exc
    except ValueError as exc:
        db.commit()
        raise HTTPException(422, str(exc)) from exc

    variant_id = None
    if payload.save_variant:
        variant = Response(
            kind=ResponseKind.TRANSFORMED.value,
            origin=(
                ResponseOrigin.DEMO_FIXTURE.value
                if result.is_synthetic or source.is_synthetic
                else ResponseOrigin.API.value
            ),
            parent_response_id=source.id,
            question_id=source.question_id,
            learner_profile_id=source.learner_profile_id,
            prompt_version_id=source.prompt_version_id,
            provider=payload.provider.value,
            model_id=payload.model_id,
            label=f"{source.label or 'response'} + {'+'.join(result.applied_treatments)}",
            system_prompt_snapshot="(see transformation_meta.stages)",
            user_prompt_snapshot="(ad-hoc transformation from the workbench)",
            generation_settings=settings,
            requested_settings=settings,
            control_limitations=result.control_limitations,
            text=result.text,
            applied_treatments=result.applied_treatments,
            transformation_meta={
                "treatment_order": result.treatment_order,
                "stages": result.stage_summary(),
                "analysis": result.analysis,
                "plan": result.plan,
                "changes": [
                    {
                        "treatment": c.treatment,
                        "name": c.name,
                        "stats": c.stats,
                        "unified_diff": c.unified_diff[:20000],
                    }
                    for c in result.changes
                ],
                "source_response_id": source.id,
            },
            cost_usd=result.total_cost_usd,
            is_synthetic=result.is_synthetic or source.is_synthetic,
        )
        db.add(variant)
        db.flush()
        variant_id = variant.id

        if result.fidelity:
            db.add(
                FidelityReport(
                    response_id=variant.id,
                    source_response_id=source.id,
                    provider=payload.provider.value,
                    model_id=payload.model_id,
                    warnings=result.fidelity.get("warnings") or [],
                    checklist_coverage=result.fidelity.get("checklist_coverage") or [],
                    verdict=result.fidelity.get("verdict", "unreviewed"),
                    numeric_drift=result.fidelity.get("numeric_drift") or [],
                    is_synthetic=variant.is_synthetic,
                )
            )
        db.add(
            TextMetrics(
                response_id=variant.id,
                metrics=compute_metrics(
                    variant.text,
                    factual_checklist=list(question.factual_checklist or []) if question else [],
                ),
            )
        )

    db.commit()
    return {
        "variant_response_id": variant_id,
        "text": result.text,
        "applied_treatments": result.applied_treatments,
        "treatment_order": result.treatment_order,
        "analysis": result.analysis,
        "plan": result.plan,
        "fidelity": result.fidelity,
        "changes": [
            {
                "treatment": c.treatment,
                "name": c.name,
                "stats": c.stats,
                "unified_diff": c.unified_diff,
                "text_after": c.text_after,
            }
            for c in result.changes
        ],
        "stages": result.stage_summary(),
        "total_cost_usd": result.total_cost_usd,
        "is_synthetic": result.is_synthetic,
        "control_limitations": result.control_limitations,
    }


@router.post("/responses/{response_id}/concept-graph", status_code=201)
def build_concept_graph(
    response_id: str,
    provider: str = Query(...),
    model_id: str = Query(...),
    effort: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Extract and validate a concept dependency graph for one response."""
    response = _get_response(db, response_id)
    pipeline = TransformationPipeline(db)
    try:
        raw, _record, _cost, synthetic = pipeline._stage_concept_graph(  # noqa: SLF001
            response.text,
            response.question.text if response.question else "",
            PipelineConfig(treatments=[], provider=provider, model_id=model_id, effort=effort),
        )
    except ProviderError as exc:
        db.commit()
        raise HTTPException(502, {"message": str(exc), "error_type": exc.error_type}) from exc

    validated = graph_utils.validate(raw)
    sequencing = graph_utils.sequencing_violations(response.text, validated)

    record = ConceptGraph(
        response_id=response.id,
        nodes=validated.nodes,
        edges=validated.edges,
        teaching_order=validated.teaching_order,
        cycles_detected=validated.cycles,
        provider=provider,
        model_id=model_id,
        is_hypothesis=True,
        is_synthetic=synthetic or response.is_synthetic,
    )
    db.add(record)
    db.commit()

    return {
        "id": record.id,
        **validated.as_dict(),
        "sequencing_analysis": sequencing,
        "is_synthetic": record.is_synthetic,
        "disclaimer": (
            "Prerequisite relationships are inferred by a language model. Treat every "
            "edge as a hypothesis about conceptual dependency, not established fact."
        ),
    }


@router.post("/responses/judge", status_code=201)
def judge_responses(payload: JudgeRequest, db: Session = Depends(get_db)) -> dict:
    """Queue blinded judge evaluations.

    Judging is queued rather than synchronous because a comparison screen can
    easily ask for dozens of evaluations at once.
    """
    if not payload.response_ids:
        raise HTTPException(422, "Provide at least one response id.")

    found = list(
        db.execute(select(Response.id).where(Response.id.in_(payload.response_ids))).scalars()
    )
    missing = set(payload.response_ids) - set(found)
    if missing:
        raise HTTPException(404, f"Unknown response ids: {sorted(missing)}")

    job = queue.enqueue(
        db,
        kind=JobKind.JUDGE_EVALUATION,
        payload={
            "response_ids": found,
            "provider": payload.provider.value,
            "model_id": payload.model_id,
            "effort": payload.effort,
        },
        progress_total=len(found),
    )
    db.commit()
    return {
        "job_id": job.id,
        "queued": len(found),
        "note": (
            "Judge scores are one model's opinion, recorded as such. They are not "
            "comprehension evidence."
        ),
    }


@router.post("/responses/{response_id}/judge-now", status_code=201)
def judge_one_now(
    response_id: str, payload: JudgeRequest, db: Session = Depends(get_db)
) -> dict:
    """Synchronous single evaluation, for the comparison workspace."""
    response = _get_response(db, response_id)
    profile = response.learner_profile
    try:
        evaluation = judge_response(
            db,
            response,
            provider=payload.provider.value,
            model_id=payload.model_id,
            learner_description=(
                f"{profile.level}: {profile.description}" if profile else "unspecified"
            ),
            question_text=response.question.text if response.question else "",
            effort=payload.effort,
        )
    except ProviderError as exc:
        db.commit()
        raise HTTPException(502, {"message": str(exc), "error_type": exc.error_type}) from exc

    db.commit()
    return {
        "id": evaluation.id,
        "scores": evaluation.scores,
        "overall_notes": evaluation.overall_notes,
        "blinded": evaluation.blinded,
        "is_synthetic": evaluation.is_synthetic,
        "evidence_class": "ai_judge_opinion",
    }


@router.post("/fidelity-reports/{report_id}/review")
def mark_fidelity_reviewed(
    report_id: str, payload: dict, db: Session = Depends(get_db)
) -> dict:
    """Record that a human checked a fidelity report."""
    report = db.get(FidelityReport, report_id)
    if report is None:
        raise HTTPException(404, "Fidelity report not found.")
    report.reviewed_by_human = True
    if payload.get("verdict") in {"clean", "warnings", "serious_concerns"}:
        report.verdict = payload["verdict"]
    db.commit()
    return {"id": report.id, "verdict": report.verdict, "reviewed_by_human": True}
