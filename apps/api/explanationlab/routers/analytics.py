"""Dashboard, results analytics, and usage/cost tracking."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..analytics import aggregate, stats
from ..db import get_db
from ..gateway import spend_today
from ..models import (
    Experiment,
    JudgeEvaluation,
    Response,
    TextMetrics,
    UsageRecord,
    utcnow,
)
from ..security import require_researcher

router = APIRouter(dependencies=[Depends(require_researcher)], tags=["analytics"])


@router.get("/analytics/overview")
def overview(db: Session = Depends(get_db)) -> dict:
    return aggregate.overview(db)


@router.get("/analytics/experiments/{experiment_id}")
def experiment_analytics(experiment_id: str, db: Session = Depends(get_db)) -> dict:
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(404, "Experiment not found.")
    return aggregate.experiment_summary(db, experiment)


@router.get("/analytics/breakdown")
def breakdown(
    group_by: str = Query(default="model", pattern="^(model|provider|treatment|domain|learner_level)$"),
    metric: str = Query(default="judge_clarity"),
    include_synthetic: bool = False,
    db: Session = Depends(get_db),
) -> dict:
    """Cross-cutting comparison for the results dashboard.

    Slices one metric by model, provider, treatment, topic domain or learner
    level. Synthetic rows are excluded by default so the dashboard shows real
    data unless the researcher asks otherwise.
    """
    stmt = select(Response)
    if not include_synthetic:
        stmt = stmt.where(Response.is_synthetic.is_(False))
    responses = list(db.execute(stmt).scalars())
    if not responses:
        # Same payload shape as a populated result, so the UI has one contract.
        return {
            "group_by": group_by,
            "metric": metric,
            "evidence_class": (
                "ai_judge_opinion" if metric.startswith("judge_") else "automated_diagnostic"
            ),
            "groups": [],
            "include_synthetic": include_synthetic,
            "note": (
                "No matching responses yet."
                + (
                    " Synthetic demo rows are excluded by default; pass "
                    "include_synthetic=true to see demo data."
                    if not include_synthetic
                    else ""
                )
            ),
            "caveat": (
                "Neither diagnostics nor judge scores measure comprehension. For that, "
                "compare human study results."
            ),
        }

    ids = [r.id for r in responses]
    metrics_by_response = {
        m.response_id: m.metrics
        for m in db.execute(select(TextMetrics).where(TextMetrics.response_id.in_(ids))).scalars()
    }
    judges_by_response: dict[str, list] = {}
    for ev in db.execute(
        select(JudgeEvaluation).where(JudgeEvaluation.response_id.in_(ids))
    ).scalars():
        judges_by_response.setdefault(ev.response_id, []).append(ev)

    groups: dict[str, list[float]] = {}
    distinct_questions: dict[str, set] = {}

    for response in responses:
        keys = _group_keys(response, group_by)
        value = _metric_value(response, metric, metrics_by_response, judges_by_response)
        if value is None:
            continue
        for key in keys:
            groups.setdefault(key, []).append(value)
            distinct_questions.setdefault(key, set()).add(response.question_id)

    return {
        "group_by": group_by,
        "metric": metric,
        "evidence_class": (
            "ai_judge_opinion" if metric.startswith("judge_") else "automated_diagnostic"
        ),
        "groups": [
            {
                "key": key,
                **stats.summarise(values).as_dict(),
                "independence_warnings": stats.independence_warnings(
                    observation_count=len(values),
                    distinct_questions=len(distinct_questions.get(key, set())),
                ),
            }
            for key, values in sorted(groups.items())
        ],
        "include_synthetic": include_synthetic,
        "caveat": (
            "Neither diagnostics nor judge scores measure comprehension. For that, "
            "compare human study results."
        ),
    }


def _group_keys(response: Response, group_by: str) -> list[str]:
    if group_by == "model":
        return [f"{response.provider}/{response.model_id}"]
    if group_by == "provider":
        return [response.provider]
    if group_by == "treatment":
        treatments = response.applied_treatments or []
        return treatments or ["(untransformed)"]
    if group_by == "domain":
        return [response.question.domain if response.question else "(unknown)"]
    if group_by == "learner_level":
        return [
            response.learner_profile.level if response.learner_profile else "(unspecified)"
        ]
    return ["(all)"]


_DIAGNOSTIC_METRICS = {
    "word_count": ("surface", "word_count"),
    "avg_sentence_words": ("surface", "avg_sentence_words"),
    "flesch_reading_ease": ("readability", "flesch_reading_ease"),
    "jargon_candidates": ("jargon", "candidate_count"),
    "indirection_phrases": ("jargon", "indirection_phrase_count"),
    "unresolved_references": ("unresolved_references", "count"),
    "causal_density_per_100w": ("explanation_steps", "causal_density_per_100w"),
    "checklist_coverage_ratio": ("concept_coverage", "coverage_ratio"),
    "latency_ms": None,
    "cost_usd": None,
    "output_tokens": None,
}


def _metric_value(
    response: Response, metric: str, metrics_by_response: dict, judges_by_response: dict
) -> float | None:
    if metric.startswith("judge_"):
        dimension = metric.removeprefix("judge_")
        values = [
            s["score"]
            for ev in judges_by_response.get(response.id, [])
            for s in (ev.scores or [])
            if s.get("metric") == dimension and isinstance(s.get("score"), (int, float))
        ]
        return sum(values) / len(values) if values else None

    if metric in {"latency_ms", "cost_usd", "output_tokens"}:
        value = getattr(response, metric, None)
        return float(value) if value is not None else None

    path = _DIAGNOSTIC_METRICS.get(metric)
    if path is None:
        return None
    cursor = metrics_by_response.get(response.id) or {}
    for key in path:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(key)
    return float(cursor) if isinstance(cursor, (int, float)) else None


@router.get("/analytics/cost-latency")
def cost_latency_tradeoff(
    include_synthetic: bool = False, db: Session = Depends(get_db)
) -> dict:
    """What each technique costs in money and time.

    §5 asks how much additional cost and latency each technique requires; this
    is that answer, grouped by treatment set.
    """
    stmt = select(Response)
    if not include_synthetic:
        stmt = stmt.where(Response.is_synthetic.is_(False))
    responses = list(db.execute(stmt).scalars())

    groups: dict[str, dict[str, list[float]]] = {}
    for response in responses:
        key = "+".join(response.applied_treatments or []) or "(untransformed)"
        bucket = groups.setdefault(key, {"cost": [], "latency": [], "output_tokens": []})
        if response.cost_usd:
            bucket["cost"].append(float(response.cost_usd))
        if response.latency_ms is not None:
            bucket["latency"].append(float(response.latency_ms))
        if response.output_tokens:
            bucket["output_tokens"].append(float(response.output_tokens))

    return {
        "groups": [
            {
                "treatments": key,
                "n": max(len(v["cost"]), len(v["latency"])),
                "cost_usd": stats.summarise(v["cost"]).as_dict(),
                "latency_ms": stats.summarise(v["latency"]).as_dict(),
                "output_tokens": stats.summarise(v["output_tokens"]).as_dict(),
            }
            for key, v in sorted(groups.items())
        ],
        "note": (
            "Transformed variants include the cost of every pipeline stage "
            "(analysis, planning, each treatment, fidelity), which is why a "
            "transformation costs several times a single generation."
        ),
    }


@router.get("/usage")
def usage(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> dict:
    """Spend, tokens, errors and cache effectiveness."""
    since = utcnow() - timedelta(days=days)

    by_purpose = db.execute(
        select(
            UsageRecord.purpose,
            func.count(UsageRecord.id),
            func.coalesce(func.sum(UsageRecord.input_tokens), 0),
            func.coalesce(func.sum(UsageRecord.output_tokens), 0),
            func.coalesce(func.sum(UsageRecord.cost_usd), 0.0),
        )
        .where(UsageRecord.created_at >= since, UsageRecord.is_synthetic.is_(False))
        .group_by(UsageRecord.purpose)
    ).all()

    by_model = db.execute(
        select(
            UsageRecord.provider,
            UsageRecord.model_id,
            func.count(UsageRecord.id),
            func.coalesce(func.sum(UsageRecord.cost_usd), 0.0),
            func.avg(UsageRecord.latency_ms),
        )
        .where(UsageRecord.created_at >= since, UsageRecord.is_synthetic.is_(False))
        .group_by(UsageRecord.provider, UsageRecord.model_id)
    ).all()

    errors = db.execute(
        select(
            UsageRecord.error_type,
            func.count(UsageRecord.id),
        )
        .where(UsageRecord.created_at >= since, UsageRecord.success.is_(False))
        .group_by(UsageRecord.error_type)
    ).all()

    recent_errors = list(
        db.execute(
            select(UsageRecord)
            .where(UsageRecord.success.is_(False))
            .order_by(UsageRecord.created_at.desc())
            .limit(20)
        ).scalars()
    )

    cache_hits = db.execute(
        select(func.count(UsageRecord.id)).where(
            UsageRecord.created_at >= since, UsageRecord.served_from_cache.is_(True)
        )
    ).scalar_one()
    total_calls = db.execute(
        select(func.count(UsageRecord.id)).where(UsageRecord.created_at >= since)
    ).scalar_one()

    from ..config import get_settings

    settings = get_settings()
    today = spend_today(db)

    return {
        "window_days": days,
        "by_purpose": [
            {
                "purpose": purpose,
                "calls": int(calls),
                "input_tokens": int(inp),
                "output_tokens": int(out),
                "estimated_cost_usd": round(float(cost), 4),
            }
            for purpose, calls, inp, out, cost in by_purpose
        ],
        "by_model": [
            {
                "provider": provider,
                "model_id": model_id,
                "calls": int(calls),
                "estimated_cost_usd": round(float(cost), 4),
                "avg_latency_ms": round(float(latency), 1) if latency is not None else None,
            }
            for provider, model_id, calls, cost, latency in by_model
        ],
        "errors": {
            "by_type": [{"error_type": t or "unknown", "count": int(c)} for t, c in errors],
            "recent": [
                {
                    "created_at": e.created_at.isoformat(),
                    "provider": e.provider,
                    "model_id": e.model_id,
                    "purpose": e.purpose,
                    "error_type": e.error_type,
                    "error_message": e.error_message,
                }
                for e in recent_errors
            ],
        },
        "cache": {
            "hits": int(cache_hits),
            "total_calls": int(total_calls),
            "hit_rate": round(cache_hits / total_calls, 3) if total_calls else None,
        },
        "spend_controls": {
            "spent_today_usd": round(today, 4),
            "daily_cap_usd": settings.daily_spend_cap_usd,
            "remaining_today_usd": round(
                max(0.0, settings.daily_spend_cap_usd - today), 4
            ),
            "cap_reached": today >= settings.daily_spend_cap_usd,
        },
        "note": (
            "Costs are estimates from the configured per-model prices and "
            "provider-reported token counts. Demo-mode calls are excluded. Check your "
            "provider dashboard for authoritative billing."
        ),
    }
