"""Experiment orchestration.

The lifecycle required by §15:

    Draft -> Configured -> Running -> Completed/Failed -> Evaluated -> Reported

Conditions are expanded from a compact specification into one row per
experimental cell, and runs into one row per (condition x question x replicate).
Each run is independently executable and independently retryable, which is what
makes "retry failed tasks without duplicating completed records" true by
construction rather than by careful coding at the call site.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..enums import (
    CallPurpose,
    ExperimentStatus,
    ExperimentType,
    PromptCondition,
    ResponseKind,
    ResponseOrigin,
    RunStatus,
    Treatment,
)
from ..evaluation.metrics import compute_metrics
from ..gateway import call_model, catalog_entry
from ..models import (
    ConceptGraph,
    Experiment,
    ExperimentCondition,
    ExperimentQuestion,
    ExperimentRun,
    FidelityReport,
    LearnerProfile,
    ModelCatalogEntry,
    PromptVersion,
    ResearchQuestion,
    Response,
    TextMetrics,
    utcnow,
)
from ..prompts import registry as prompt_registry
from ..providers.base import GenerationRequest, ProviderError
from ..providers.catalog import estimate_cost_usd
from ..transformations.pipeline import (
    LearnerContext,
    PipelineConfig,
    TransformationPipeline,
)
from ..transformations.strategies import ordered_treatments


class ConfigurationError(ValueError):
    pass


@dataclass(slots=True)
class ModelRef:
    provider: str
    model_id: str


@dataclass(slots=True)
class ExperimentSpec:
    """Compact description a researcher submits; expanded into conditions."""

    name: str
    type: str
    question_ids: list[str]
    source_models: list[ModelRef] = field(default_factory=list)
    prompt_template_keys: list[str] = field(default_factory=list)
    treatment_sets: list[list[str]] = field(default_factory=list)
    transform_models: list[ModelRef] = field(default_factory=list)
    learner_profile_id: str | None = None
    base_prompt_key: str = "condition_a_default"
    generation_settings: dict = field(default_factory=dict)
    transform_settings: dict = field(default_factory=dict)
    objective: str = ""
    hypothesis: str = ""
    seed: int = 20261022
    repetitions: int = 1
    run_fidelity: bool = True
    run_analysis: bool = True
    run_planning: bool = True
    build_concept_graph: bool = False
    include_untransformed_control: bool = True


# ---------------------------------------------------------------------------
# Condition expansion
# ---------------------------------------------------------------------------


def _resolve_prompt(db: Session, key: str) -> PromptVersion:
    version = prompt_registry.version_by_key(db, key)
    if version is None:
        raise ConfigurationError(f"Unknown prompt template '{key}'.")
    return version


def _validate_models(db: Session, refs: list[ModelRef], label: str) -> None:
    for ref in refs:
        entry = catalog_entry(db, ref.provider, ref.model_id)
        if entry is None:
            raise ConfigurationError(
                f"{label} model '{ref.model_id}' ({ref.provider}) is not in the catalogue. "
                "Add it, or refresh the catalogue from the provider."
            )
        if not entry.is_enabled:
            raise ConfigurationError(
                f"{label} model '{ref.model_id}' is disabled in the catalogue."
            )


def build_conditions(db: Session, spec: ExperimentSpec) -> list[dict]:
    """Expand the specification into experimental cells."""
    if not spec.question_ids:
        raise ConfigurationError("Select at least one research question.")
    if not spec.source_models:
        raise ConfigurationError("Select at least one source model.")

    _validate_models(db, spec.source_models, "Source")
    _validate_models(db, spec.transform_models, "Transformation")

    if spec.type == ExperimentType.BASELINE.value:
        return _baseline_conditions(db, spec)
    if spec.type == ExperimentType.PROMPT_INTERVENTION.value:
        return _prompt_conditions(db, spec)
    if spec.type == ExperimentType.ABLATION.value:
        return _ablation_conditions(db, spec)
    if spec.type == ExperimentType.CROSS_MODEL.value:
        return _cross_model_conditions(db, spec)
    if spec.type == ExperimentType.HUMAN_STUDY.value:
        raise ConfigurationError(
            "Experiment 5 does not generate responses. Create a human study from "
            "existing response variants instead."
        )
    raise ConfigurationError(f"Unknown experiment type '{spec.type}'.")


def _baseline_conditions(db: Session, spec: ExperimentSpec) -> list[dict]:
    """Experiment 1: default behaviour, one arm per model, no tutor prompt."""
    version = _resolve_prompt(db, "condition_a_default")
    if version.template.condition != PromptCondition.DEFAULT.value:
        raise ConfigurationError(
            "The baseline condition must use the default prompt template. Adding a "
            "pedagogical prompt here would contaminate the baseline."
        )
    return [
        {
            "label": f"Baseline — {ref.provider}/{ref.model_id}",
            "provider": ref.provider,
            "model_id": ref.model_id,
            "prompt_version_id": version.id,
            "treatments": [],
            "order_index": i,
        }
        for i, ref in enumerate(spec.source_models)
    ]


def _prompt_conditions(db: Session, spec: ExperimentSpec) -> list[dict]:
    """Experiment 2: models x prompt conditions (A/B/C required)."""
    keys = spec.prompt_template_keys or [
        "condition_a_default",
        "condition_b_generic_tutor",
        "condition_c_structured_pedagogical",
    ]
    versions = [_resolve_prompt(db, k) for k in keys]

    present = {v.template.condition for v in versions}
    required = {
        PromptCondition.DEFAULT.value,
        PromptCondition.GENERIC_TUTOR.value,
        PromptCondition.STRUCTURED_PEDAGOGICAL.value,
    }
    missing = required - present
    if missing:
        raise ConfigurationError(
            "A prompt-intervention experiment needs all three required conditions. "
            f"Missing: {', '.join(sorted(missing))}."
        )

    conditions = []
    i = 0
    for ref in spec.source_models:
        for version in versions:
            conditions.append(
                {
                    "label": f"{version.template.name} — {ref.provider}/{ref.model_id}",
                    "provider": ref.provider,
                    "model_id": ref.model_id,
                    "prompt_version_id": version.id,
                    "treatments": [],
                    "order_index": i,
                }
            )
            i += 1
    return conditions


def _ablation_conditions(db: Session, spec: ExperimentSpec) -> list[dict]:
    """Experiment 3: one arm per treatment set, plus an untransformed control."""
    sets = spec.treatment_sets or [[t.value] for t in Treatment]
    base = _resolve_prompt(db, spec.base_prompt_key)

    conditions: list[dict] = []
    i = 0
    for ref in spec.source_models:
        transformer = spec.transform_models[0] if spec.transform_models else ref

        if spec.include_untransformed_control:
            conditions.append(
                {
                    "label": f"Control (untransformed) — {ref.provider}/{ref.model_id}",
                    "provider": ref.provider,
                    "model_id": ref.model_id,
                    "prompt_version_id": base.id,
                    "treatments": [],
                    "order_index": i,
                }
            )
            i += 1

        for treatments in sets:
            valid = [t.key for t in ordered_treatments(treatments)]
            if not valid:
                raise ConfigurationError(f"Treatment set {treatments!r} contains no valid treatments.")
            conditions.append(
                {
                    "label": f"{'+'.join(valid)} — {ref.provider}/{ref.model_id}",
                    "provider": ref.provider,
                    "model_id": ref.model_id,
                    "prompt_version_id": base.id,
                    "treatments": valid,
                    "transform_provider": transformer.provider,
                    "transform_model_id": transformer.model_id,
                    "order_index": i,
                }
            )
            i += 1
    return conditions


def _cross_model_conditions(db: Session, spec: ExperimentSpec) -> list[dict]:
    """Experiment 4: generator x transformer, so the two are separable.

    The point of the cross is to tell apart "the methodology works" from "the
    transforming model is just better". Without every generator x transformer
    cell, that distinction is unavailable.
    """
    if not spec.transform_models:
        raise ConfigurationError(
            "A cross-model experiment needs at least one transformation model, "
            "configured separately from the source model."
        )
    sets = spec.treatment_sets or [[t.value for t in Treatment]]
    base = _resolve_prompt(db, spec.base_prompt_key)

    conditions: list[dict] = []
    i = 0
    for ref in spec.source_models:
        if spec.include_untransformed_control:
            conditions.append(
                {
                    "label": f"Source only — {ref.provider}/{ref.model_id}",
                    "provider": ref.provider,
                    "model_id": ref.model_id,
                    "prompt_version_id": base.id,
                    "treatments": [],
                    "order_index": i,
                }
            )
            i += 1
        for transformer in spec.transform_models:
            for treatments in sets:
                valid = [t.key for t in ordered_treatments(treatments)]
                conditions.append(
                    {
                        "label": (
                            f"{ref.model_id} generates -> {transformer.model_id} "
                            f"transforms [{'+'.join(valid)}]"
                        ),
                        "provider": ref.provider,
                        "model_id": ref.model_id,
                        "prompt_version_id": base.id,
                        "treatments": valid,
                        "transform_provider": transformer.provider,
                        "transform_model_id": transformer.model_id,
                        "order_index": i,
                    }
                )
                i += 1
    return conditions


# ---------------------------------------------------------------------------
# Cost / request estimation
# ---------------------------------------------------------------------------

# Rough per-call token assumptions for pre-flight estimates only. Actual usage
# is always recorded from the provider's own counts.
_EST_INPUT_TOKENS = {"generation": 400, "stage": 2200, "treatment": 2600}
_EST_OUTPUT_TOKENS = {"generation": 900, "stage": 700, "treatment": 1100}


def calls_per_run(condition: dict, spec: ExperimentSpec) -> int:
    calls = 1  # source generation
    treatments = condition.get("treatments") or []
    if treatments:
        if spec.run_analysis:
            calls += 1
        if spec.run_planning:
            calls += 1
        calls += len(treatments)
        if spec.run_fidelity:
            calls += 1
    if spec.build_concept_graph:
        calls += 1
    return calls


def estimate(db: Session, spec: ExperimentSpec, conditions: list[dict]) -> dict:
    """Pre-flight request count and estimated spend."""
    settings = get_settings()
    total_calls = 0
    total_cost = 0.0
    per_condition = []

    for condition in conditions:
        calls = calls_per_run(condition, spec)
        runs = len(spec.question_ids) * max(1, spec.repetitions)
        condition_calls = calls * runs

        src = catalog_entry(db, condition["provider"], condition["model_id"])
        tgt = (
            catalog_entry(
                db, condition.get("transform_provider"), condition.get("transform_model_id")
            )
            if condition.get("transform_model_id")
            else src
        )

        gen_cost = estimate_cost_usd(
            _EST_INPUT_TOKENS["generation"],
            _EST_OUTPUT_TOKENS["generation"],
            src.input_cost_per_mtok if src else None,
            src.output_cost_per_mtok if src else None,
        )
        other_calls = calls - 1
        other_cost = other_calls * estimate_cost_usd(
            _EST_INPUT_TOKENS["treatment"],
            _EST_OUTPUT_TOKENS["treatment"],
            tgt.input_cost_per_mtok if tgt else None,
            tgt.output_cost_per_mtok if tgt else None,
        )
        cost = (gen_cost + other_cost) * runs

        total_calls += condition_calls
        total_cost += cost
        per_condition.append(
            {
                "label": condition["label"],
                "calls_per_run": calls,
                "runs": runs,
                "total_calls": condition_calls,
                "estimated_cost_usd": round(cost, 4),
            }
        )

    exceeds_batch_limit = total_calls > settings.max_batch_requests
    return {
        "total_model_calls": total_calls,
        "total_runs": len(conditions) * len(spec.question_ids) * max(1, spec.repetitions),
        "condition_count": len(conditions),
        "estimated_cost_usd": round(total_cost, 4),
        "per_condition": per_condition,
        "max_batch_requests": settings.max_batch_requests,
        "exceeds_batch_limit": exceeds_batch_limit,
        "requires_confirmation": total_cost > settings.cost_confirmation_threshold_usd,
        "confirmation_threshold_usd": settings.cost_confirmation_threshold_usd,
        "demo_mode": settings.demo_mode,
        "note": (
            "Estimates use fixed token assumptions and configured prices; actual spend "
            "is recorded from provider-reported usage. In demo mode no spend occurs."
        ),
    }


# ---------------------------------------------------------------------------
# Materialisation
# ---------------------------------------------------------------------------


def create_experiment(db: Session, spec: ExperimentSpec) -> tuple[Experiment, dict]:
    """Validate, expand and persist an experiment in `configured` state."""
    conditions = build_conditions(db, spec)
    projection = estimate(db, spec, conditions)

    if projection["exceeds_batch_limit"]:
        raise ConfigurationError(
            f"This configuration needs {projection['total_model_calls']} model calls, "
            f"over the limit of {projection['max_batch_requests']}. Reduce questions, "
            "conditions or repetitions, or raise MAX_BATCH_REQUESTS."
        )

    questions = db.execute(
        select(ResearchQuestion).where(ResearchQuestion.id.in_(spec.question_ids))
    ).scalars().all()
    found = {q.id for q in questions}
    missing = set(spec.question_ids) - found
    if missing:
        raise ConfigurationError(f"Unknown research question ids: {sorted(missing)}")

    experiment = Experiment(
        name=spec.name,
        type=spec.type,
        status=ExperimentStatus.CONFIGURED.value,
        objective=spec.objective,
        hypothesis=spec.hypothesis,
        seed=spec.seed,
        repetitions=max(1, spec.repetitions),
        estimated_cost_usd=projection["estimated_cost_usd"],
        config={
            "spec": {
                "source_models": [vars(m) for m in spec.source_models],
                "transform_models": [vars(m) for m in spec.transform_models],
                "prompt_template_keys": spec.prompt_template_keys,
                "treatment_sets": spec.treatment_sets,
                "base_prompt_key": spec.base_prompt_key,
                "learner_profile_id": spec.learner_profile_id,
                "generation_settings": spec.generation_settings,
                "transform_settings": spec.transform_settings,
                "run_analysis": spec.run_analysis,
                "run_planning": spec.run_planning,
                "run_fidelity": spec.run_fidelity,
                "build_concept_graph": spec.build_concept_graph,
                "include_untransformed_control": spec.include_untransformed_control,
            },
            "estimate": projection,
            "prompt_guard_note": prompt_registry.BASELINE_GUARD_NOTE,
        },
    )
    db.add(experiment)
    db.flush()

    for i, qid in enumerate(spec.question_ids):
        db.add(ExperimentQuestion(experiment_id=experiment.id, question_id=qid, order_index=i))

    for payload in conditions:
        condition = ExperimentCondition(
            experiment_id=experiment.id,
            label=payload["label"],
            order_index=payload.get("order_index", 0),
            provider=payload["provider"],
            model_id=payload["model_id"],
            prompt_version_id=payload.get("prompt_version_id"),
            learner_profile_id=spec.learner_profile_id,
            generation_settings=spec.generation_settings,
            treatments=payload.get("treatments") or [],
            transform_provider=payload.get("transform_provider"),
            transform_model_id=payload.get("transform_model_id"),
            transform_settings=spec.transform_settings,
        )
        db.add(condition)
        db.flush()

        for qid in spec.question_ids:
            for replicate in range(max(1, spec.repetitions)):
                db.add(
                    ExperimentRun(
                        experiment_id=experiment.id,
                        condition_id=condition.id,
                        question_id=qid,
                        replicate_index=replicate,
                        status=RunStatus.PENDING.value,
                    )
                )

    db.flush()
    return experiment, projection


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def execute_run(db: Session, run: ExperimentRun) -> Response:
    """Execute one run: generate, then transform if the condition calls for it.

    Idempotent on success: a run already marked succeeded returns its existing
    response rather than generating a second one, so a retry of a partially
    failed batch cannot duplicate completed work.
    """
    if run.status == RunStatus.SUCCEEDED.value and run.responses:
        return _final_response(run)

    condition = run.condition
    question = run.question
    profile = (
        db.get(LearnerProfile, condition.learner_profile_id)
        if condition.learner_profile_id
        else None
    )
    spec_cfg = (run.experiment.config or {}).get("spec", {})

    run.status = RunStatus.RUNNING.value
    run.attempts += 1
    run.started_at = utcnow()
    run.error = None
    run.error_type = None
    db.flush()

    try:
        source = _generate_source(db, run, condition, question, profile)
        final = source

        if condition.treatments:
            final = _apply_transformations(
                db, run, condition, question, profile, source, spec_cfg
            )

        if spec_cfg.get("build_concept_graph"):
            _maybe_graph(db, run, condition, question, source, spec_cfg)

        run.status = RunStatus.SUCCEEDED.value
        run.finished_at = utcnow()
        db.flush()
        return final

    except Exception as exc:
        run.status = RunStatus.FAILED.value
        run.finished_at = utcnow()
        run.error = str(exc)[:4000]
        run.error_type = getattr(exc, "error_type", type(exc).__name__)
        db.flush()
        raise


def _generate_source(
    db: Session,
    run: ExperimentRun,
    condition: ExperimentCondition,
    question: ResearchQuestion,
    profile: LearnerProfile | None,
) -> Response:
    # Cross-model conditions may reuse an existing answer as the source rather
    # than regenerating it.
    if condition.source_response_id:
        existing = db.get(Response, condition.source_response_id)
        if existing is None:
            raise ConfigurationError(
                f"Condition references missing source response {condition.source_response_id}."
            )
        return existing

    version = (
        db.get(PromptVersion, condition.prompt_version_id)
        if condition.prompt_version_id
        else None
    )
    system, user = prompt_registry.render(version, question, profile)
    settings = condition.generation_settings or {}

    outcome = call_model(
        db,
        provider=condition.provider,
        model_id=condition.model_id,
        request=GenerationRequest(
            system=system,
            user=user,
            max_output_tokens=int(settings.get("max_output_tokens", 4096)),
            temperature=settings.get("temperature"),
            effort=settings.get("effort"),
        ),
        purpose=CallPurpose.GENERATION,
        experiment_id=run.experiment_id,
    )
    result = outcome.result

    limitations = list(result.control_limitations)
    limitations.append(prompt_registry.BASELINE_GUARD_NOTE)

    response = Response(
        kind=ResponseKind.SOURCE.value,
        origin=(
            ResponseOrigin.DEMO_FIXTURE.value
            if result.is_synthetic
            else ResponseOrigin.API.value
        ),
        run_id=run.id,
        question_id=question.id,
        learner_profile_id=profile.id if profile else None,
        prompt_version_id=condition.prompt_version_id,
        provider=condition.provider,
        model_id=condition.model_id,
        label=condition.label,
        system_prompt_snapshot=system,
        user_prompt_snapshot=user,
        generation_settings=result.effective_settings,
        requested_settings=settings,
        control_limitations=limitations,
        text=result.text,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        latency_ms=result.latency_ms,
        cost_usd=outcome.cost_usd,
        finish_reason=result.finish_reason,
        request_hash=None,
        served_from_cache=result.served_from_cache,
        is_synthetic=result.is_synthetic,
    )
    db.add(response)
    db.flush()
    _store_metrics(db, response, question)
    return response


def _apply_transformations(
    db: Session,
    run: ExperimentRun,
    condition: ExperimentCondition,
    question: ResearchQuestion,
    profile: LearnerProfile | None,
    source: Response,
    spec_cfg: dict,
) -> Response:
    transform_settings = condition.transform_settings or {}
    pipeline = TransformationPipeline(db, experiment_id=run.experiment_id)

    learner = LearnerContext(
        level=profile.level if profile else "unspecified",
        description=profile.description if profile else "",
        assumed_prior_knowledge=", ".join(profile.assumed_prior_knowledge or [])
        if profile
        else "unspecified",
        unfamiliar_with=", ".join(profile.unfamiliar_with or []) if profile else "unspecified",
    )

    result = pipeline.run(
        source_text=source.text,
        question_text=question.text,
        learner=learner,
        config=PipelineConfig(
            treatments=list(condition.treatments or []),
            provider=condition.transform_provider or condition.provider,
            model_id=condition.transform_model_id or condition.model_id,
            effort=transform_settings.get("effort"),
            temperature=transform_settings.get("temperature"),
            max_output_tokens=int(transform_settings.get("max_output_tokens", 6000)),
            run_analysis=bool(spec_cfg.get("run_analysis", True)),
            run_planning=bool(spec_cfg.get("run_planning", True)),
            run_fidelity=bool(spec_cfg.get("run_fidelity", True)),
            build_concept_graph=False,  # handled separately against the source
            factual_checklist=list(question.factual_checklist or []),
        ),
    )

    transformed = Response(
        kind=ResponseKind.TRANSFORMED.value,
        origin=(
            ResponseOrigin.DEMO_FIXTURE.value
            if result.is_synthetic or source.is_synthetic
            else ResponseOrigin.API.value
        ),
        run_id=run.id,
        parent_response_id=source.id,
        question_id=question.id,
        learner_profile_id=profile.id if profile else None,
        prompt_version_id=condition.prompt_version_id,
        provider=condition.transform_provider or condition.provider,
        model_id=condition.transform_model_id or condition.model_id,
        label=f"{condition.label} [transformed]",
        system_prompt_snapshot="(see transformation_meta.stages)",
        user_prompt_snapshot="(see transformation_meta.changes)",
        generation_settings=transform_settings,
        requested_settings=transform_settings,
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
        # Synthetic provenance is inherited: a real transformation of a fixture
        # is still not evidence.
        is_synthetic=result.is_synthetic or source.is_synthetic,
    )
    db.add(transformed)
    db.flush()

    if result.fidelity:
        db.add(
            FidelityReport(
                response_id=transformed.id,
                source_response_id=source.id,
                provider=transformed.provider,
                model_id=transformed.model_id,
                warnings=result.fidelity.get("warnings") or [],
                checklist_coverage=result.fidelity.get("checklist_coverage") or [],
                verdict=result.fidelity.get("verdict", "unreviewed"),
                numeric_drift=result.fidelity.get("numeric_drift") or [],
                is_synthetic=transformed.is_synthetic,
            )
        )

    _store_metrics(db, transformed, question)
    db.flush()
    return transformed


def _maybe_graph(
    db: Session,
    run: ExperimentRun,
    condition: ExperimentCondition,
    question: ResearchQuestion,
    source: Response,
    spec_cfg: dict,
) -> None:
    from ..concepts import graph as graph_utils

    pipeline = TransformationPipeline(db, experiment_id=run.experiment_id)
    raw, _record, _cost, synthetic = pipeline._stage_concept_graph(  # noqa: SLF001
        source.text,
        question.text,
        PipelineConfig(
            treatments=[],
            provider=condition.transform_provider or condition.provider,
            model_id=condition.transform_model_id or condition.model_id,
            effort=(condition.transform_settings or {}).get("effort"),
        ),
    )
    validated = graph_utils.validate(raw)
    db.add(
        ConceptGraph(
            response_id=source.id,
            nodes=validated.nodes,
            edges=validated.edges,
            teaching_order=validated.teaching_order,
            cycles_detected=validated.cycles,
            provider=condition.transform_provider or condition.provider,
            model_id=condition.transform_model_id or condition.model_id,
            is_hypothesis=True,
            is_synthetic=synthetic or source.is_synthetic,
        )
    )
    db.flush()


def _store_metrics(db: Session, response: Response, question: ResearchQuestion | None) -> None:
    metrics = compute_metrics(
        response.text,
        factual_checklist=list(question.factual_checklist or []) if question else [],
    )
    db.merge(TextMetrics(response_id=response.id, metrics=metrics, metrics_version=metrics["metrics_version"]))
    db.flush()


def _final_response(run: ExperimentRun) -> Response:
    transformed = [r for r in run.responses if r.kind == ResponseKind.TRANSFORMED.value]
    if transformed:
        return sorted(transformed, key=lambda r: r.created_at)[-1]
    return sorted(run.responses, key=lambda r: r.created_at)[-1]


def pending_runs(db: Session, experiment_id: str) -> list[ExperimentRun]:
    return list(
        db.execute(
            select(ExperimentRun)
            .where(
                ExperimentRun.experiment_id == experiment_id,
                ExperimentRun.status.in_([RunStatus.PENDING.value, RunStatus.FAILED.value]),
            )
            .order_by(ExperimentRun.created_at)
        ).scalars()
    )


def refresh_experiment_status(db: Session, experiment: Experiment) -> None:
    runs = list(
        db.execute(
            select(ExperimentRun).where(ExperimentRun.experiment_id == experiment.id)
        ).scalars()
    )
    if not runs:
        return
    statuses = {r.status for r in runs}
    if RunStatus.PENDING.value in statuses or RunStatus.RUNNING.value in statuses:
        experiment.status = ExperimentStatus.RUNNING.value
    elif statuses == {RunStatus.FAILED.value}:
        experiment.status = ExperimentStatus.FAILED.value
        experiment.finished_at = utcnow()
    else:
        # Partial failure still counts as completed-with-errors; the run table
        # carries the detail and the UI shows failed counts.
        experiment.status = ExperimentStatus.COMPLETED.value
        experiment.finished_at = utcnow()
    db.flush()
