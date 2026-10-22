"""Exports: CSV, JSON and a human-readable Markdown report.

Every export carries its provenance and its caveats. A CSV that leaves the tool
without the note that half its rows are demo fixtures is how synthetic data ends
up in a paper.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..analytics import aggregate
from ..models import (
    Experiment,
    ExperimentRun,
    FidelityReport,
    JudgeEvaluation,
    Study,
    TextMetrics,
)

SYNTHETIC_BANNER = (
    "!!! CONTAINS SYNTHETIC DEMO DATA — NOT RESEARCH FINDINGS !!! "
    "Rows flagged is_synthetic were produced by local fixtures in demo mode, not by "
    "a model. Do not report them as results."
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


def experiment_json(db: Session, experiment: Experiment) -> dict:
    """Full reproducible record of an experiment."""
    runs = list(
        db.execute(
            select(ExperimentRun).where(ExperimentRun.experiment_id == experiment.id)
        ).scalars()
    )
    response_rows = []
    for run in runs:
        for response in run.responses:
            metrics = db.execute(
                select(TextMetrics).where(TextMetrics.response_id == response.id)
            ).scalar_one_or_none()
            judges = list(
                db.execute(
                    select(JudgeEvaluation).where(JudgeEvaluation.response_id == response.id)
                ).scalars()
            )
            fidelity = list(
                db.execute(
                    select(FidelityReport).where(FidelityReport.response_id == response.id)
                ).scalars()
            )
            response_rows.append(
                {
                    "id": response.id,
                    "run_id": run.id,
                    "condition_id": run.condition_id,
                    "question_id": response.question_id,
                    "replicate_index": run.replicate_index,
                    "kind": response.kind,
                    "origin": response.origin,
                    "provider": response.provider,
                    "model_id": response.model_id,
                    "parent_response_id": response.parent_response_id,
                    "applied_treatments": response.applied_treatments,
                    "prompt_version_id": response.prompt_version_id,
                    "system_prompt_snapshot": response.system_prompt_snapshot,
                    "user_prompt_snapshot": response.user_prompt_snapshot,
                    "requested_settings": response.requested_settings,
                    "effective_settings": response.generation_settings,
                    "control_limitations": response.control_limitations,
                    "text": response.text,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "latency_ms": response.latency_ms,
                    "cost_usd": response.cost_usd,
                    "served_from_cache": response.served_from_cache,
                    "is_synthetic": response.is_synthetic,
                    "created_at": response.created_at.isoformat(),
                    "transformation_meta": response.transformation_meta,
                    "automated_diagnostics": metrics.metrics if metrics else None,
                    "ai_judge_evaluations": [
                        {
                            "judge_provider": j.provider,
                            "judge_model": j.model_id,
                            "rubric": f"{j.rubric_key} v{j.rubric_version}",
                            "blinded": j.blinded,
                            "scores": j.scores,
                            "overall_notes": j.overall_notes,
                            "is_synthetic": j.is_synthetic,
                        }
                        for j in judges
                    ],
                    "fidelity_reports": [
                        {
                            "verdict": f.verdict,
                            "warnings": f.warnings,
                            "numeric_drift": f.numeric_drift,
                            "source_response_id": f.source_response_id,
                            "reviewed_by_human": f.reviewed_by_human,
                            "provisional": True,
                        }
                        for f in fidelity
                    ],
                }
            )

    contains_synthetic = any(r["is_synthetic"] for r in response_rows)
    return {
        "export_format": "explanationlab.experiment.v1",
        "exported_at": _now(),
        "contains_synthetic_data": contains_synthetic,
        "warning": SYNTHETIC_BANNER if contains_synthetic else None,
        "experiment": {
            "id": experiment.id,
            "name": experiment.name,
            "type": experiment.type,
            "status": experiment.status,
            "objective": experiment.objective,
            "hypothesis": experiment.hypothesis,
            "researcher_notes": experiment.researcher_notes,
            "seed": experiment.seed,
            "repetitions": experiment.repetitions,
            "config": experiment.config,
            "created_at": experiment.created_at.isoformat(),
        },
        "conditions": [
            {
                "id": c.id,
                "label": c.label,
                "provider": c.provider,
                "model_id": c.model_id,
                "prompt_version_id": c.prompt_version_id,
                "treatments": c.treatments,
                "transform_provider": c.transform_provider,
                "transform_model_id": c.transform_model_id,
                "generation_settings": c.generation_settings,
                "transform_settings": c.transform_settings,
                "learner_profile_id": c.learner_profile_id,
            }
            for c in sorted(experiment.conditions, key=lambda c: c.order_index)
        ],
        "questions": [
            {
                "id": eq.question.id,
                "text": eq.question.text,
                "domain": eq.question.domain,
                "conceptual_difficulty": eq.question.conceptual_difficulty,
                "factual_checklist": eq.question.factual_checklist,
            }
            for eq in sorted(experiment.questions, key=lambda q: q.order_index)
        ],
        "runs": [
            {
                "id": r.id,
                "condition_id": r.condition_id,
                "question_id": r.question_id,
                "replicate_index": r.replicate_index,
                "status": r.status,
                "attempts": r.attempts,
                "error": r.error,
                "error_type": r.error_type,
            }
            for r in runs
        ],
        "responses": response_rows,
        "summary": aggregate.experiment_summary(db, experiment),
    }


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

_CSV_COLUMNS = [
    "response_id",
    "experiment_id",
    "experiment_type",
    "condition_label",
    "question_id",
    "question_text",
    "domain",
    "conceptual_difficulty",
    "replicate_index",
    "response_kind",
    "origin",
    "is_synthetic",
    "provider",
    "model_id",
    "transform_model_id",
    "applied_treatments",
    "prompt_version_id",
    "learner_profile_id",
    "requested_temperature",
    "effective_settings",
    "control_limitations",
    "word_count",
    "avg_sentence_words",
    "flesch_reading_ease",
    "jargon_candidates",
    "indirection_phrases",
    "unresolved_references",
    "heading_count",
    "causal_density_per_100w",
    "checklist_coverage_ratio",
    "judge_mean_clarity",
    "judge_mean_mechanism",
    "fidelity_verdict",
    "fidelity_warning_count",
    "input_tokens",
    "output_tokens",
    "latency_ms",
    "cost_usd",
    "served_from_cache",
    "created_at",
]


def experiment_csv(db: Session, experiment: Experiment) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")

    payload = experiment_json(db, experiment)
    if payload["contains_synthetic_data"]:
        writer.writerow([f"# {SYNTHETIC_BANNER}"])
    writer.writerow(
        [
            f"# ExplanationLab export | experiment={experiment.name!r} | "
            f"exported_at={payload['exported_at']} | "
            "diagnostics are surface signals, judge scores are model opinions"
        ]
    )
    writer.writerow(_CSV_COLUMNS)

    conditions = {c.id: c for c in experiment.conditions}
    questions = {eq.question.id: eq.question for eq in experiment.questions}
    runs = {r["id"]: r for r in payload["runs"]}

    for row in payload["responses"]:
        condition = conditions.get(row["condition_id"])
        question = questions.get(row["question_id"])
        diag = row["automated_diagnostics"] or {}
        judges = row["ai_judge_evaluations"]
        fidelity = row["fidelity_reports"]

        writer.writerow(
            [
                row["id"],
                experiment.id,
                experiment.type,
                condition.label if condition else "",
                row["question_id"] or "",
                question.text if question else "",
                question.domain if question else "",
                question.conceptual_difficulty if question else "",
                runs.get(row["run_id"], {}).get("replicate_index", ""),
                row["kind"],
                row["origin"],
                row["is_synthetic"],
                row["provider"],
                row["model_id"],
                condition.transform_model_id if condition else "",
                "+".join(row["applied_treatments"] or []),
                row["prompt_version_id"] or "",
                condition.learner_profile_id if condition else "",
                (row["requested_settings"] or {}).get("temperature", ""),
                json.dumps(row["effective_settings"] or {}, sort_keys=True),
                " | ".join(row["control_limitations"] or []),
                _dig(diag, ("surface", "word_count")),
                _dig(diag, ("surface", "avg_sentence_words")),
                _dig(diag, ("readability", "flesch_reading_ease")),
                _dig(diag, ("jargon", "candidate_count")),
                _dig(diag, ("jargon", "indirection_phrase_count")),
                _dig(diag, ("unresolved_references", "count")),
                _dig(diag, ("structure", "heading_count")),
                _dig(diag, ("explanation_steps", "causal_density_per_100w")),
                _dig(diag, ("concept_coverage", "coverage_ratio")),
                _judge_metric(judges, "clarity"),
                _judge_metric(judges, "mechanism_explanation"),
                fidelity[0]["verdict"] if fidelity else "",
                len(fidelity[0]["warnings"]) if fidelity else "",
                row["input_tokens"],
                row["output_tokens"],
                row["latency_ms"],
                row["cost_usd"],
                row["served_from_cache"],
                row["created_at"],
            ]
        )
    return buffer.getvalue()


def _dig(payload: dict, path: tuple[str, ...]):
    cursor = payload
    for key in path:
        if not isinstance(cursor, dict):
            return ""
        cursor = cursor.get(key)
    return "" if cursor is None else cursor


def _judge_metric(judges: list[dict], metric: str):
    values = [
        s["score"]
        for j in judges
        for s in (j.get("scores") or [])
        if s.get("metric") == metric and isinstance(s.get("score"), (int, float))
    ]
    return round(sum(values) / len(values), 3) if values else ""


def study_csv(db: Session, study: Study) -> str:
    """One row per participant submission. Anonymous codes only."""
    from ..models import ParticipantSubmission, StudyAssignment
    from ..studies.scoring import summarise_submission

    assignments = {
        a.id: a
        for a in db.execute(
            select(StudyAssignment).where(StudyAssignment.study_id == study.id)
        ).scalars()
    }
    submissions = list(
        db.execute(
            select(ParticipantSubmission).where(
                ParticipantSubmission.assignment_id.in_(list(assignments) or [""])
            )
        ).scalars()
    )
    conditions = {c.id: c for c in study.conditions}

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    any_synthetic = any(c.response.is_synthetic for c in study.conditions)
    if any_synthetic:
        writer.writerow([f"# {SYNTHETIC_BANNER}"])
    writer.writerow(
        [
            f"# ExplanationLab human study export | study={study.name!r} | "
            f"exported_at={_now()} | perceived clarity is NOT comprehension"
        ]
    )
    writer.writerow(
        [
            "submission_id",
            "participant_code",
            "condition_label",
            "response_id",
            "stimulus_model_id",
            "stimulus_treatments",
            "stimulus_is_synthetic",
            "self_reported_level",
            "comprehension_score",
            "comprehension_complete",
            "pending_grading_items",
            "misconception_count",
            "perceived_clarity",
            "cognitive_effort",
            "reading_seconds",
            "assessment_seconds",
            "submitted_at",
        ]
    )

    for submission in submissions:
        summary = summarise_submission(db, submission)
        assignment = assignments.get(submission.assignment_id)
        condition = conditions.get(assignment.condition_id) if assignment else None
        writer.writerow(
            [
                submission.id,
                summary["participant_code"],
                condition.label if condition else "",
                condition.response_id if condition else "",
                condition.response.model_id if condition else "",
                "+".join(condition.response.applied_treatments or []) if condition else "",
                condition.response.is_synthetic if condition else "",
                assignment.self_reported_level if assignment else "",
                summary["comprehension_score"],
                summary["comprehension_complete"],
                summary["pending_grading_items"],
                summary["misconception_count"],
                summary["perceived_clarity"],
                summary["cognitive_effort"],
                summary["reading_seconds"],
                summary["assessment_seconds"],
                submission.created_at.isoformat(),
            ]
        )
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


def experiment_markdown(db: Session, experiment: Experiment) -> str:
    summary = aggregate.experiment_summary(db, experiment)
    lines: list[str] = []

    if summary["contains_synthetic_data"]:
        lines += [
            "> **WARNING — CONTAINS SYNTHETIC DEMO DATA**",
            ">",
            "> Some or all responses in this experiment were produced by local demo",
            "> fixtures, not by a model. Nothing below is a research finding.",
            "",
        ]

    lines += [
        f"# {experiment.name}",
        "",
        f"*Report generated {_now()} by ExplanationLab.*",
        "",
        "## Objective",
        "",
        experiment.objective or "_Not recorded._",
        "",
        "## Hypothesis",
        "",
        experiment.hypothesis or "_Not recorded._",
        "",
        "## Experimental conditions",
        "",
        "| Condition | Source model | Prompt | Treatments | Transformer |",
        "| --- | --- | --- | --- | --- |",
    ]
    for c in sorted(experiment.conditions, key=lambda c: c.order_index):
        treatments = "+".join(c.treatments or []) or "—"
        lines.append(
            f"| {c.label} | `{c.provider}/{c.model_id}` | "
            f"`{c.prompt_version_id or '—'}` | {treatments} | "
            f"`{c.transform_model_id or '—'}` |"
        )

    lines += [
        "",
        "## Dataset",
        "",
        f"- Questions: **{len(summary['questions'])}**",
        f"- Replicates per cell: **{experiment.repetitions}**",
        f"- Randomisation seed: `{experiment.seed}`",
        "",
        "| Question | Domain | Conceptual difficulty |",
        "| --- | --- | --- |",
    ]
    for q in summary["questions"]:
        lines.append(f"| {q['text']} | {q['domain']} | {q['conceptual_difficulty']} |")

    lines += [
        "",
        "## Model and generation configuration",
        "",
        "Controls that could not be applied are listed per condition below. ",
        "Current frontier models reject `temperature`, so conditions are **not** ",
        "temperature-matched; this is recorded rather than glossed over.",
        "",
        "## Evaluation methodology",
        "",
        "Three measurement categories, kept separate:",
        "",
        "1. **Automated diagnostics** — deterministic surface measures. Describe text; ",
        "   do not measure understanding.",
        "2. **AI judge opinion** — a configurable judge model, blinded to model identity, ",
        "   scoring an anchored rubric. An opinion, not evidence of comprehension.",
        "3. **Human comprehension** — not present in this report unless a linked human ",
        "   study was run. See the study report.",
        "",
        "## Results",
        "",
    ]

    for condition in summary["conditions"]:
        lines += [
            f"### {condition['label']}",
            "",
            f"- Runs: {condition['runs']['succeeded']} succeeded, "
            f"{condition['runs']['failed']} failed, {condition['runs']['pending']} pending",
            f"- Responses analysed: {condition['response_count']}",
            f"- Estimated spend: ${condition['operations']['total_cost_usd']:.4f}",
        ]
        if condition["contains_synthetic"]:
            lines.append("- **Contains synthetic fixture data.**")

        diag = condition["automated_diagnostics"].get("metrics", {})
        if diag:
            lines += ["", "**Automated diagnostics** (mean [95% interval] where n permits)", ""]
            lines += ["| Metric | Mean | Interval | n |", "| --- | --- | --- | --- |"]
            for name, value in diag.items():
                interval = (
                    f"{value['ci_low']} – {value['ci_high']}"
                    if value.get("ci_low") is not None
                    else "n too small"
                )
                lines.append(f"| {name} | {value['mean']} | {interval} | {value['n']} |")

        judge = condition["ai_judge"]
        if judge.get("metrics"):
            lines += [
                "",
                f"**AI judge opinion** (judges: {', '.join(judge['judge_models'])}, n={judge['n']})",
                "",
                "| Dimension | Mean (1–5) | Interval | n |",
                "| --- | --- | --- | --- |",
            ]
            for name, value in judge["metrics"].items():
                interval = (
                    f"{value['ci_low']} – {value['ci_high']}"
                    if value.get("ci_low") is not None
                    else "n too small"
                )
                lines.append(f"| {name} | {value['mean']} | {interval} | {value['n']} |")
            for warning in judge.get("independence_warnings", []):
                lines.append(f"> {warning}")

        fidelity = condition["fidelity"]
        if fidelity.get("reports"):
            lines += [
                "",
                f"**Factual fidelity** — {fidelity['reports']} report(s), "
                f"{fidelity['high_severity_warnings']} high-severity warning(s)",
                "",
            ]
            for wtype, count in sorted(
                fidelity["warning_counts_by_type"].items(), key=lambda kv: -kv[1]
            ):
                lines.append(f"- `{wtype}`: {count}")
            lines.append(
                "> Provisional. A clean verdict means no problem was detected, not that "
                "the transformation is verified accurate."
            )

        if condition["control_limitations"]:
            lines += ["", "**Control limitations**", ""]
            for limitation in condition["control_limitations"]:
                lines.append(f"- {limitation}")
        lines.append("")

    lines += [
        "## Limitations",
        "",
        "- Automated diagnostics and judge scores are **not** comprehension measures. ",
        "  No claim about teaching effectiveness follows from them.",
        "- Generation conditions are not fully matched across providers; see the ",
        "  control limitations recorded per condition.",
        "- Sample sizes at this scale are exploratory. Intervals are wide and ",
        "  observations within a condition are clustered by question and by model ",
        "  response, so the effective n is smaller than the row count.",
        "- Fidelity verdicts are provisional assessments, partly produced by an LLM.",
        "- An LLM-inferred concept dependency graph is a hypothesis about prerequisite ",
        "  structure, not validated ground truth.",
        "",
        "## Researcher notes",
        "",
        experiment.researcher_notes or "_None recorded._",
        "",
        "---",
        "",
        "*Evidence standard: this report distinguishes automated diagnostics, AI judge ",
        "opinions, human preference and actual human comprehension. A higher judge score ",
        "is not evidence that a model teaches better.*",
    ]
    return "\n".join(lines)


def study_markdown(db: Session, study: Study) -> str:
    results = aggregate.study_results(db, study)
    lines: list[str] = []

    if results["contains_synthetic_data"]:
        lines += [
            "> **WARNING — a stimulus in this study is synthetic demo text.**",
            "> Participant responses may be real, but they responded to fixture text.",
            "",
        ]

    lines += [
        f"# Human comprehension study — {study.name}",
        "",
        f"*Report generated {_now()}.*",
        "",
        "## Design",
        "",
        f"- Conditions: **{len(results['conditions'])}** (blinded to participants)",
        f"- Allocation: randomised, seed `{study.seed}`"
        + (", balanced across arms" if study.balance_conditions else ", unbalanced"),
        f"- Participants assigned: **{results['totals']['assigned']}**",
        f"- Submissions: **{results['totals']['submitted']}**",
        "",
        "Participants saw explanation text only. Model identity, condition label and ",
        "treatment names were never sent to the participant interface.",
        "",
        "## Results by condition",
        "",
    ]

    for condition in results["conditions"]:
        comp = condition["human_comprehension"]["overall"]
        pref = condition["human_preference"]
        interval = (
            f"{comp['ci_low']} – {comp['ci_high']}"
            if comp.get("ci_low") is not None
            else "n too small for an interval"
        )
        lines += [
            f"### {condition['label']}",
            "",
            f"- Stimulus: `{condition['model_id']}`"
            + (
                f" with {'+'.join(condition['treatments'])}"
                if condition["treatments"]
                else " (untransformed)"
            ),
            f"- Submitted: {condition['participants']['submitted']} "
            f"(assigned {condition['participants']['assigned']}, "
            f"withdrawn {condition['participants']['withdrawn']})",
            "",
            "**Human comprehension (primary evidence)**",
            "",
            f"- Score: **{comp['mean']}** (95% interval {interval}, n={comp['n']})",
            f"- Misconception rate: {condition['human_comprehension']['misconception_rate']}",
            f"- Ungraded free-text items: {condition['human_comprehension']['pending_grading_items']}",
            "",
            "**Self-reported (reported separately, never averaged in)**",
            "",
            f"- Perceived clarity: {pref['perceived_clarity']['mean']} (n={pref['perceived_clarity']['n']})",
            f"- Cognitive effort: {pref['cognitive_effort']['mean']} (n={pref['cognitive_effort']['n']})",
            "",
            "**Time**",
            "",
            f"- Reading: {condition['time']['reading_seconds']['mean']} s",
            f"- Assessment: {condition['time']['assessment_seconds']['mean']} s",
            "",
        ]
        for dimension, value in condition["human_comprehension"]["by_dimension"].items():
            lines.append(f"- {dimension}: {value['mean']} (n={value['n']})")
        lines.append("")

    lines += ["## Limitations", ""]
    for warning in results["warnings"]:
        lines.append(f"- {warning}")
    lines += [
        "- Perceived clarity can move in the opposite direction to comprehension ",
        "  (illusion-of-fluency effect). Read the two together.",
        "- Participants self-select; this is not a representative sample.",
        "- AI-suggested grades, where used, are suggestions. Only human scores and ",
        "  objective auto-scores contribute to the figures above.",
        "",
        "## Notable findings",
        "",
        "_To be written by the researcher. The platform deliberately does not generate ",
        "conclusions from these numbers._",
        "",
    ]
    return "\n".join(lines)
