"""Aggregation for the results and analytics screens.

The four evidence categories stay structurally separate all the way to the API
payload: ``automated_diagnostics``, ``ai_judge``, ``human_preference`` and
``human_comprehension`` are distinct keys with distinct ``evidence_class``
labels. Nothing merges them, and no endpoint returns an "overall score".

Synthetic contamination is computed, not assumed: if any contributing row is a
demo fixture, the aggregate says so.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..enums import (
    EvidenceClass,
    ResponseKind,
    RunStatus,
    StudyStatus,
)
from ..models import (
    Experiment,
    ExperimentRun,
    FidelityReport,
    JudgeEvaluation,
    ParticipantSubmission,
    Response,
    Study,
    StudyAssignment,
    TextMetrics,
    UsageRecord,
)
from ..studies.scoring import summarise_submission
from . import stats

# Diagnostic fields surfaced in comparisons. Chosen because each is directly
# interpretable; the full payload is always available per response.
_DIAGNOSTIC_PATHS = [
    ("word_count", ("surface", "word_count")),
    ("avg_sentence_words", ("surface", "avg_sentence_words")),
    ("long_sentence_share", ("surface", "long_sentence_share")),
    ("max_paragraph_words", ("surface", "max_paragraph_words")),
    ("flesch_reading_ease", ("readability", "flesch_reading_ease")),
    ("flesch_kincaid_grade", ("readability", "flesch_kincaid_grade")),
    ("jargon_candidates", ("jargon", "candidate_count")),
    ("nominalisation_density", ("jargon", "nominalisation_density")),
    ("indirection_phrases", ("jargon", "indirection_phrase_count")),
    ("unresolved_references", ("unresolved_references", "count")),
    ("heading_count", ("structure", "heading_count")),
    ("causal_density_per_100w", ("explanation_steps", "causal_density_per_100w")),
    ("repeated_trigrams", ("repetition", "repeated_trigram_count")),
    ("checklist_coverage_ratio", ("concept_coverage", "coverage_ratio")),
    ("terms_undefined_share", ("terminology_introduction", "undefined_share")),
]


def _dig(payload: dict, path: tuple[str, ...]):
    cursor = payload
    for key in path:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(key)
    return cursor


def overview(db: Session) -> dict:
    """Dashboard counts. Every number is a real database count."""
    experiment_count = db.execute(select(func.count(Experiment.id))).scalar_one()
    completed_runs = db.execute(
        select(func.count(ExperimentRun.id)).where(
            ExperimentRun.status == RunStatus.SUCCEEDED.value
        )
    ).scalar_one()
    failed_runs = db.execute(
        select(func.count(ExperimentRun.id)).where(
            ExperimentRun.status == RunStatus.FAILED.value
        )
    ).scalar_one()
    response_count = db.execute(select(func.count(Response.id))).scalar_one()
    synthetic_responses = db.execute(
        select(func.count(Response.id)).where(Response.is_synthetic.is_(True))
    ).scalar_one()

    models_evaluated = db.execute(
        select(func.count(func.distinct(Response.model_id))).where(Response.model_id != "")
    ).scalar_one()

    active_studies = db.execute(
        select(func.count(Study.id)).where(Study.status == StudyStatus.OPEN.value)
    ).scalar_one()
    submissions = db.execute(select(func.count(ParticipantSubmission.id))).scalar_one()

    usage = db.execute(
        select(
            func.coalesce(func.sum(UsageRecord.input_tokens), 0),
            func.coalesce(func.sum(UsageRecord.output_tokens), 0),
            func.coalesce(func.sum(UsageRecord.cost_usd), 0.0),
            func.count(UsageRecord.id),
        ).where(UsageRecord.is_synthetic.is_(False))
    ).one()

    errors = db.execute(
        select(func.count(UsageRecord.id)).where(UsageRecord.success.is_(False))
    ).scalar_one()
    cache_hits = db.execute(
        select(func.count(UsageRecord.id)).where(UsageRecord.served_from_cache.is_(True))
    ).scalar_one()

    judged = db.execute(
        select(func.count(func.distinct(JudgeEvaluation.response_id)))
    ).scalar_one()
    with_metrics = db.execute(select(func.count(TextMetrics.id))).scalar_one()

    recent = list(
        db.execute(
            select(Experiment).order_by(Experiment.created_at.desc()).limit(8)
        ).scalars()
    )

    return {
        "experiments": {
            "total": experiment_count,
            "by_status": _count_by(db, Experiment.status, Experiment.id),
        },
        "runs": {"completed": completed_runs, "failed": failed_runs},
        "responses": {
            "total": response_count,
            "synthetic": synthetic_responses,
            "real": response_count - synthetic_responses,
        },
        "models_evaluated": models_evaluated,
        "human_studies": {"active": active_studies, "submissions": submissions},
        "usage": {
            "input_tokens": int(usage[0]),
            "output_tokens": int(usage[1]),
            "estimated_cost_usd": round(float(usage[2]), 4),
            "calls": int(usage[3]),
            "errors": errors,
            "cache_hits": cache_hits,
        },
        "evaluation_coverage": {
            "responses_with_diagnostics": with_metrics,
            "responses_with_judge_opinion": judged,
            "diagnostic_coverage": round(with_metrics / response_count, 3)
            if response_count
            else None,
            "judge_coverage": round(judged / response_count, 3) if response_count else None,
        },
        "recent_experiments": [
            {
                "id": e.id,
                "name": e.name,
                "type": e.type,
                "status": e.status,
                "created_at": e.created_at.isoformat(),
            }
            for e in recent
        ],
        "contains_synthetic_data": synthetic_responses > 0,
    }


def _count_by(db: Session, column, id_column) -> dict:
    rows = db.execute(select(column, func.count(id_column)).group_by(column)).all()
    return {str(k): int(v) for k, v in rows}


# ---------------------------------------------------------------------------
# Experiment-level aggregation
# ---------------------------------------------------------------------------


def experiment_summary(db: Session, experiment: Experiment) -> dict:
    conditions = sorted(experiment.conditions, key=lambda c: c.order_index)
    runs = list(
        db.execute(
            select(ExperimentRun).where(ExperimentRun.experiment_id == experiment.id)
        ).scalars()
    )
    runs_by_condition: dict[str, list[ExperimentRun]] = {}
    for run in runs:
        runs_by_condition.setdefault(run.condition_id, []).append(run)

    per_condition = []
    any_synthetic = False

    for condition in conditions:
        condition_runs = runs_by_condition.get(condition.id, [])
        response_ids = [r.id for run in condition_runs for r in run.responses]
        responses = (
            list(
                db.execute(select(Response).where(Response.id.in_(response_ids))).scalars()
            )
            if response_ids
            else []
        )
        # The variant a reader would be shown: the transformed text if there is
        # one, otherwise the source.
        presented = _presented_responses(responses)
        any_synthetic = any_synthetic or any(r.is_synthetic for r in presented)

        per_condition.append(
            {
                "condition_id": condition.id,
                "label": condition.label,
                "provider": condition.provider,
                "model_id": condition.model_id,
                "treatments": condition.treatments,
                "transform_model_id": condition.transform_model_id,
                "runs": {
                    "total": len(condition_runs),
                    "succeeded": sum(
                        1 for r in condition_runs if r.status == RunStatus.SUCCEEDED.value
                    ),
                    "failed": sum(
                        1 for r in condition_runs if r.status == RunStatus.FAILED.value
                    ),
                    "pending": sum(
                        1 for r in condition_runs if r.status == RunStatus.PENDING.value
                    ),
                },
                "response_count": len(presented),
                "contains_synthetic": any(r.is_synthetic for r in presented),
                "automated_diagnostics": _diagnostics_for(db, presented),
                "ai_judge": _judge_for(db, presented),
                "fidelity": _fidelity_for(db, presented),
                "operations": _operations_for(presented),
                "control_limitations": sorted(
                    {lim for r in presented for lim in (r.control_limitations or [])}
                ),
            }
        )

    return {
        "experiment": {
            "id": experiment.id,
            "name": experiment.name,
            "type": experiment.type,
            "status": experiment.status,
            "objective": experiment.objective,
            "hypothesis": experiment.hypothesis,
            "seed": experiment.seed,
            "repetitions": experiment.repetitions,
            "estimated_cost_usd": experiment.estimated_cost_usd,
        },
        "conditions": per_condition,
        "contains_synthetic_data": any_synthetic,
        "evidence_note": (
            "Diagnostics describe texts; judge scores are one model's opinion. Neither "
            "is comprehension evidence. Run a human study (Experiment 5) for that."
        ),
        "questions": [
            {
                "id": eq.question.id,
                "text": eq.question.text,
                "domain": eq.question.domain,
                "conceptual_difficulty": eq.question.conceptual_difficulty,
            }
            for eq in sorted(experiment.questions, key=lambda q: q.order_index)
        ],
    }


def _presented_responses(responses: list[Response]) -> list[Response]:
    by_run: dict[str | None, list[Response]] = {}
    for r in responses:
        by_run.setdefault(r.run_id, []).append(r)
    presented = []
    for group in by_run.values():
        transformed = [r for r in group if r.kind == ResponseKind.TRANSFORMED.value]
        pool = transformed or group
        presented.append(sorted(pool, key=lambda r: r.created_at)[-1])
    return presented


def _diagnostics_for(db: Session, responses: list[Response]) -> dict:
    if not responses:
        return {"evidence_class": EvidenceClass.AUTOMATED_DIAGNOSTIC.value, "metrics": {}, "n": 0}

    ids = [r.id for r in responses]
    rows = list(
        db.execute(select(TextMetrics).where(TextMetrics.response_id.in_(ids))).scalars()
    )
    collected: dict[str, list[float]] = {name: [] for name, _ in _DIAGNOSTIC_PATHS}
    for row in rows:
        for name, path in _DIAGNOSTIC_PATHS:
            value = _dig(row.metrics or {}, path)
            if isinstance(value, (int, float)):
                collected[name].append(float(value))

    return {
        "evidence_class": EvidenceClass.AUTOMATED_DIAGNOSTIC.value,
        "n": len(rows),
        "metrics": {
            name: stats.summarise(values).as_dict()
            for name, values in collected.items()
            if values
        },
        "caveat": (
            "Surface diagnostics. Do not rank conditions by these; readability indices "
            "in particular are not comprehension measures."
        ),
    }


def _judge_for(db: Session, responses: list[Response]) -> dict:
    if not responses:
        return {"evidence_class": EvidenceClass.AI_JUDGE_OPINION.value, "n": 0, "metrics": {}}

    ids = [r.id for r in responses]
    evaluations = list(
        db.execute(
            select(JudgeEvaluation).where(JudgeEvaluation.response_id.in_(ids))
        ).scalars()
    )
    by_metric: dict[str, list[float]] = {}
    judge_models = set()
    for ev in evaluations:
        judge_models.add(f"{ev.provider}:{ev.model_id}")
        for score in ev.scores or []:
            metric = score.get("metric")
            value = score.get("score")
            if metric and isinstance(value, (int, float)):
                by_metric.setdefault(metric, []).append(float(value))

    warnings = stats.independence_warnings(
        observation_count=len(evaluations),
        distinct_responses=len({ev.response_id for ev in evaluations}),
    )

    return {
        "evidence_class": EvidenceClass.AI_JUDGE_OPINION.value,
        "n": len(evaluations),
        "judge_models": sorted(judge_models),
        "metrics": {m: stats.summarise(v).as_dict() for m, v in by_metric.items()},
        "independence_warnings": warnings,
        "caveat": (
            "A judge model's opinion, subject to position, verbosity and "
            "self-enhancement bias. Not evidence that a human understood anything."
        ),
    }


def _fidelity_for(db: Session, responses: list[Response]) -> dict:
    ids = [r.id for r in responses]
    if not ids:
        return {"reports": 0}
    reports = list(
        db.execute(
            select(FidelityReport).where(FidelityReport.response_id.in_(ids))
        ).scalars()
    )
    by_verdict: dict[str, int] = {}
    by_type: dict[str, int] = {}
    high_severity = 0
    for report in reports:
        by_verdict[report.verdict] = by_verdict.get(report.verdict, 0) + 1
        for warning in report.warnings or []:
            wtype = warning.get("type", "unknown")
            by_type[wtype] = by_type.get(wtype, 0) + 1
            if warning.get("severity") == "high":
                high_severity += 1

    return {
        "reports": len(reports),
        "by_verdict": by_verdict,
        "warning_counts_by_type": by_type,
        "high_severity_warnings": high_severity,
        "numeric_drift_reports": sum(1 for r in reports if r.numeric_drift),
        "human_reviewed": sum(1 for r in reports if r.reviewed_by_human),
        "caveat": (
            "Provisional. A 'clean' verdict means no problem was detected, not that "
            "the transformation is verified accurate."
        ),
    }


def _operations_for(responses: list[Response]) -> dict:
    latencies = [r.latency_ms for r in responses if r.latency_ms is not None]
    costs = [r.cost_usd for r in responses if r.cost_usd]
    out_tokens = [r.output_tokens for r in responses if r.output_tokens]
    return {
        "latency_ms": stats.summarise([float(v) for v in latencies]).as_dict()
        if latencies
        else None,
        "total_cost_usd": round(sum(costs), 6),
        "output_tokens": stats.summarise([float(v) for v in out_tokens]).as_dict()
        if out_tokens
        else None,
        "cache_hits": sum(1 for r in responses if r.served_from_cache),
    }


# ---------------------------------------------------------------------------
# Study-level aggregation (the primary evidence)
# ---------------------------------------------------------------------------


def study_results(db: Session, study: Study) -> dict:
    assignments = list(
        db.execute(
            select(StudyAssignment).where(StudyAssignment.study_id == study.id)
        ).scalars()
    )
    submissions = list(
        db.execute(
            select(ParticipantSubmission).where(
                ParticipantSubmission.assignment_id.in_([a.id for a in assignments] or [""])
            )
        ).scalars()
    )

    summaries = [summarise_submission(db, s) for s in submissions]
    by_condition: dict[str, list[dict]] = {}
    for summary in summaries:
        by_condition.setdefault(summary["condition_id"], []).append(summary)

    conditions_out = []
    any_synthetic = False
    total_pending = 0

    for condition in sorted(study.conditions, key=lambda c: c.order_index):
        group = by_condition.get(condition.id, [])
        any_synthetic = any_synthetic or bool(condition.response.is_synthetic)
        pending = sum(s["pending_grading_items"] for s in group)
        total_pending += pending

        comprehension = [
            s["comprehension_score"]
            for s in group
            if s["comprehension_score"] is not None and s["comprehension_complete"]
        ]
        clarity = [s["perceived_clarity"] for s in group if s["perceived_clarity"] is not None]
        effort = [s["cognitive_effort"] for s in group if s["cognitive_effort"] is not None]
        reading = [s["reading_seconds"] for s in group if s["reading_seconds"] is not None]
        assessment = [
            s["assessment_seconds"] for s in group if s["assessment_seconds"] is not None
        ]

        dimension_scores: dict[str, list[float]] = {}
        for summary in group:
            for dimension, bucket in summary["by_dimension"].items():
                if bucket.get("score_ratio") is not None and bucket.get("complete"):
                    dimension_scores.setdefault(dimension, []).append(bucket["score_ratio"])

        conditions_out.append(
            {
                "condition_id": condition.id,
                # Researcher-facing only; participants never receive this.
                "label": condition.label,
                "response_id": condition.response_id,
                "model_id": condition.response.model_id,
                "treatments": condition.response.applied_treatments,
                "contains_synthetic_stimulus": bool(condition.response.is_synthetic),
                "participants": {
                    "assigned": sum(1 for a in assignments if a.condition_id == condition.id),
                    "submitted": len(group),
                    "withdrawn": sum(
                        1
                        for a in assignments
                        if a.condition_id == condition.id and a.withdrawn_at is not None
                    ),
                },
                "human_comprehension": {
                    "evidence_class": EvidenceClass.HUMAN_COMPREHENSION.value,
                    "overall": stats.summarise(comprehension).as_dict(),
                    "by_dimension": {
                        d: stats.summarise(v).as_dict() for d, v in dimension_scores.items()
                    },
                    "misconception_rate": round(
                        sum(1 for s in group if s["misconception_count"] > 0) / len(group), 4
                    )
                    if group
                    else None,
                    "pending_grading_items": pending,
                },
                "human_preference": {
                    "evidence_class": EvidenceClass.HUMAN_PREFERENCE.value,
                    "perceived_clarity": stats.summarise([float(c) for c in clarity]).as_dict(),
                    "cognitive_effort": stats.summarise([float(e) for e in effort]).as_dict(),
                    "caveat": (
                        "Self-reported. Perceived ease can move opposite to actual "
                        "comprehension; read these alongside, never instead of, the "
                        "comprehension scores."
                    ),
                },
                "time": {
                    "reading_seconds": stats.summarise(reading).as_dict(),
                    "assessment_seconds": stats.summarise(assessment).as_dict(),
                },
            }
        )

    all_submissions = len(submissions)
    warnings = stats.independence_warnings(
        observation_count=all_submissions,
        distinct_participants=len({s.assignment.participant_code for s in submissions}),
    )
    if total_pending:
        warnings.append(
            f"{total_pending} free-text answer(s) are not yet graded. Comprehension "
            "figures exclude participants with ungraded items, so they are provisional."
        )
    if all_submissions < stats.EXPLORATORY_N_THRESHOLD:
        warnings.append(
            f"Total n={all_submissions}. This is an exploratory study; differences "
            "between conditions should not be reported as established."
        )

    return {
        "study": {
            "id": study.id,
            "name": study.name,
            "status": study.status,
            "seed": study.seed,
            "balance_conditions": study.balance_conditions,
            "question_id": study.question_id,
        },
        "conditions": conditions_out,
        "totals": {
            "assigned": len(assignments),
            "submitted": all_submissions,
            "pending_grading_items": total_pending,
        },
        "warnings": warnings,
        "contains_synthetic_data": any_synthetic,
        "paired_analysis_available": False,
        "evidence_note": (
            "Human comprehension results are the primary evidence in this platform. "
            "Perceived clarity and cognitive effort are reported separately and are "
            "never averaged into the comprehension score."
        ),
    }


def condition_comparison(db: Session, study: Study, metric: str = "comprehension") -> dict:
    """Pairwise differences between study arms, with bootstrap intervals."""
    results = study_results(db, study)
    arms = [
        (c["label"], c["human_comprehension"]["overall"], c["condition_id"])
        for c in results["conditions"]
    ]
    comparisons = []
    for i in range(len(arms)):
        for j in range(i + 1, len(arms)):
            a_label, a_stats, _ = arms[i]
            b_label, b_stats, _ = arms[j]
            if a_stats["mean"] is None or b_stats["mean"] is None:
                continue
            comparisons.append(
                {
                    "a": a_label,
                    "b": b_label,
                    "mean_a": a_stats["mean"],
                    "mean_b": b_stats["mean"],
                    "difference": round(b_stats["mean"] - a_stats["mean"], 4),
                    "n_a": a_stats["n"],
                    "n_b": b_stats["n"],
                    "note": (
                        "Difference of independent-group means. Intervals on each group "
                        "are reported separately; with these sample sizes treat the "
                        "difference as a direction to investigate, not a result."
                    ),
                }
            )
    return {
        "metric": metric,
        "comparisons": comparisons,
        "warnings": results["warnings"],
        "contains_synthetic_data": results["contains_synthetic_data"],
    }
