"""Stages A–E of the pedagogical transformation engine.

    A. Input analysis      -> structured, validated description of the source
    B. Pedagogical planning-> which techniques this explanation actually needs
    C. Controlled transform-> apply selected treatments, one at a time
    D. Fidelity verification-> deterministic checks + LLM reviewer
    E. Renderable output   -> text, per-treatment changes, warnings, metadata

Stage C applies treatments **sequentially and individually**, keeping the
intermediate text after each one. That costs more calls than a single combined
prompt, and it is the point: it is the only way to attribute a change to a
treatment, which is what Experiment 3 requires.
"""

from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from ..enums import CallPurpose
from ..gateway import call_model, call_structured
from ..prompts.safety import GUARD_INSTRUCTION, untrusted_block
from ..providers.base import GenerationRequest
from .base import (
    ANALYSIS_SCHEMA,
    CONCEPT_GRAPH_SCHEMA,
    FIDELITY_SCHEMA,
    PLAN_SCHEMA,
    schema_instruction,
)
from .fidelity import FIDELITY_SYSTEM, build_fidelity_user_prompt, run_deterministic_checks
from .strategies import STRATEGY_BY_KEY, ordered_treatments, render_instruction


@dataclass(slots=True)
class LearnerContext:
    level: str = "unspecified"
    description: str = ""
    assumed_prior_knowledge: str = "unspecified"
    unfamiliar_with: str = "unspecified"


@dataclass(slots=True)
class PipelineConfig:
    treatments: list[str]
    provider: str
    model_id: str
    effort: str | None = None
    temperature: float | None = None
    max_output_tokens: int = 6000
    run_analysis: bool = True
    run_planning: bool = True
    run_fidelity: bool = True
    build_concept_graph: bool = False
    factual_checklist: list[str] = field(default_factory=list)
    treatment_order_override: list[str] | None = None


@dataclass(slots=True)
class StageRecord:
    stage: str
    label: str
    provider: str
    model_id: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    cost_usd: float
    served_from_cache: bool
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TreatmentChange:
    treatment: str
    name: str
    text_before: str
    text_after: str
    stats: dict
    unified_diff: str


@dataclass(slots=True)
class PipelineResult:
    text: str
    applied_treatments: list[str]
    treatment_order: list[str]
    analysis: dict | None
    plan: dict | None
    fidelity: dict | None
    concept_graph: dict | None
    changes: list[TreatmentChange]
    stages: list[StageRecord]
    total_cost_usd: float
    is_synthetic: bool
    control_limitations: list[str]

    def stage_summary(self) -> list[dict]:
        return [
            {
                "stage": s.stage,
                "label": s.label,
                "provider": s.provider,
                "model_id": s.model_id,
                "input_tokens": s.input_tokens,
                "output_tokens": s.output_tokens,
                "latency_ms": s.latency_ms,
                "cost_usd": s.cost_usd,
                "served_from_cache": s.served_from_cache,
                "notes": s.notes,
            }
            for s in self.stages
        ]


# ---------------------------------------------------------------------------
# Deterministic change description
# ---------------------------------------------------------------------------

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_HEADING_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)
_LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s", re.MULTILINE)
_TABLE_RE = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)


def describe_change(before: str, after: str) -> dict:
    """Measured, model-free description of what a treatment did."""
    b_words, a_words = before.split(), after.split()
    b_sents = [s for s in _SENTENCE_RE.split(before) if s.strip()]
    a_sents = [s for s in _SENTENCE_RE.split(after) if s.strip()]

    matcher = difflib.SequenceMatcher(None, b_words, a_words)
    similarity = matcher.ratio()

    return {
        "words_before": len(b_words),
        "words_after": len(a_words),
        "word_delta": len(a_words) - len(b_words),
        "sentences_before": len(b_sents),
        "sentences_after": len(a_sents),
        "avg_sentence_words_before": round(len(b_words) / len(b_sents), 2) if b_sents else 0,
        "avg_sentence_words_after": round(len(a_words) / len(a_sents), 2) if a_sents else 0,
        "headings_added": len(_HEADING_RE.findall(after)) - len(_HEADING_RE.findall(before)),
        "list_items_added": len(_LIST_RE.findall(after)) - len(_LIST_RE.findall(before)),
        "table_rows_added": len(_TABLE_RE.findall(after)) - len(_TABLE_RE.findall(before)),
        "word_similarity": round(similarity, 4),
    }


def unified_diff(before: str, after: str, *, label: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile=f"{label}:before",
            tofile=f"{label}:after",
            lineterm="",
            n=2,
        )
    )


# ---------------------------------------------------------------------------
# The pipeline
# ---------------------------------------------------------------------------


class TransformationPipeline:
    def __init__(self, db: Session, *, experiment_id: str | None = None):
        self.db = db
        self.experiment_id = experiment_id

    def run(
        self,
        *,
        source_text: str,
        question_text: str,
        learner: LearnerContext,
        config: PipelineConfig,
    ) -> PipelineResult:
        stages: list[StageRecord] = []
        limitations: list[str] = []
        synthetic = False
        total_cost = 0.0

        treatments = (
            [STRATEGY_BY_KEY[k] for k in config.treatment_order_override if k in STRATEGY_BY_KEY]
            if config.treatment_order_override
            else ordered_treatments(config.treatments)
        )
        if not treatments:
            raise ValueError("No valid treatments selected; nothing to transform.")

        # -- Stage A -------------------------------------------------------
        analysis: dict | None = None
        if config.run_analysis:
            analysis, rec, cost, syn = self._stage_analysis(source_text, question_text, config)
            stages.append(rec)
            total_cost += cost
            synthetic = synthetic or syn
            limitations.extend(rec.notes)

        # -- Stage B -------------------------------------------------------
        plan: dict | None = None
        if config.run_planning:
            plan, rec, cost, syn = self._stage_plan(
                source_text, question_text, analysis, learner, config
            )
            stages.append(rec)
            total_cost += cost
            synthetic = synthetic or syn
            limitations.extend(rec.notes)

        # -- Stage C -------------------------------------------------------
        analysis_blob = json.dumps(analysis, indent=2) if analysis else "(analysis not run)"
        plan_blob = json.dumps(plan, indent=2) if plan else "(planning not run)"

        current = source_text
        changes: list[TreatmentChange] = []
        for strategy in treatments:
            instruction = render_instruction(
                strategy,
                source_text=untrusted_block("explanation_to_transform", current),
                question=question_text,
                analysis=analysis_blob,
                plan=plan_blob,
                learner_level=learner.level,
                learner_description=learner.description,
                assumed_prior_knowledge=learner.assumed_prior_knowledge,
                unfamiliar_with=learner.unfamiliar_with,
            )
            outcome = call_model(
                self.db,
                provider=config.provider,
                model_id=config.model_id,
                request=GenerationRequest(
                    system=(
                        "You apply one specific, bounded pedagogical transformation to a "
                        "technical explanation. You respect the stated boundaries of the "
                        "treatment exactly: doing more than asked destroys the experiment "
                        "this is part of.\n\n" + GUARD_INSTRUCTION
                    ),
                    user=instruction,
                    max_output_tokens=config.max_output_tokens,
                    temperature=config.temperature,
                    effort=config.effort,
                ),
                purpose=CallPurpose.TRANSFORMATION,
                experiment_id=self.experiment_id,
            )
            new_text = outcome.result.text.strip()
            if not new_text:
                raise ValueError(
                    f"Treatment {strategy.key} returned empty output; variant not created."
                )

            changes.append(
                TreatmentChange(
                    treatment=strategy.key,
                    name=strategy.name,
                    text_before=current,
                    text_after=new_text,
                    stats=describe_change(current, new_text),
                    unified_diff=unified_diff(current, new_text, label=strategy.key),
                )
            )
            stages.append(
                StageRecord(
                    stage="C",
                    label=f"{strategy.key} — {strategy.name}",
                    provider=outcome.result.provider,
                    model_id=outcome.result.model_id,
                    input_tokens=outcome.result.input_tokens,
                    output_tokens=outcome.result.output_tokens,
                    latency_ms=outcome.result.latency_ms,
                    cost_usd=outcome.cost_usd,
                    served_from_cache=outcome.result.served_from_cache,
                    notes=list(outcome.result.control_limitations),
                )
            )
            total_cost += outcome.cost_usd
            synthetic = synthetic or outcome.result.is_synthetic
            limitations.extend(outcome.result.control_limitations)
            current = new_text

        # -- Stage D -------------------------------------------------------
        fidelity: dict | None = None
        if config.run_fidelity:
            fidelity, rec, cost, syn = self._stage_fidelity(
                source_text, current, [t.key for t in treatments], config
            )
            stages.append(rec)
            total_cost += cost
            synthetic = synthetic or syn
            limitations.extend(rec.notes)
        else:
            det = run_deterministic_checks(source_text, current, [t.key for t in treatments])
            fidelity = {
                "verdict": "warnings" if det.warnings else "clean",
                "warnings": det.warnings,
                "numeric_drift": det.numeric_drift,
                "preserved_claims": [],
                "notes": "LLM review skipped; deterministic checks only.",
                "llm_review_ran": False,
                "provisional": True,
            }

        # -- Optional concept graph ---------------------------------------
        graph: dict | None = None
        if config.build_concept_graph:
            graph, rec, cost, syn = self._stage_concept_graph(source_text, question_text, config)
            stages.append(rec)
            total_cost += cost
            synthetic = synthetic or syn

        # -- Stage E -------------------------------------------------------
        return PipelineResult(
            text=current,
            applied_treatments=[t.key for t in treatments],
            treatment_order=[t.key for t in treatments],
            analysis=analysis,
            plan=plan,
            fidelity=fidelity,
            concept_graph=graph,
            changes=changes,
            stages=stages,
            total_cost_usd=round(total_cost, 6),
            is_synthetic=synthetic,
            control_limitations=sorted(set(limitations)),
        )

    # -- stage implementations --------------------------------------------

    def _stage_analysis(self, source_text: str, question_text: str, config: PipelineConfig):
        system = (
            "You analyse a technical explanation to describe its structure, "
            "vocabulary and gaps. You describe; you do not rewrite or improve.\n\n"
            + GUARD_INSTRUCTION
        )
        user = "\n\n".join(
            [
                f"Question the explanation answers: {question_text}",
                "Explanation to analyse:",
                untrusted_block("explanation_to_analyse", source_text),
                schema_instruction(ANALYSIS_SCHEMA, "input_analysis"),
            ]
        )
        data, outcome = call_structured(
            self.db,
            provider=config.provider,
            model_id=config.model_id,
            request=GenerationRequest(
                system=system,
                user=user,
                max_output_tokens=min(config.max_output_tokens, 4000),
                temperature=config.temperature,
                effort=config.effort,
                json_schema=ANALYSIS_SCHEMA,
                json_schema_name="input_analysis",
            ),
            purpose=CallPurpose.ANALYSIS,
            experiment_id=self.experiment_id,
        )
        return (
            data,
            self._record("A", "Input analysis", outcome),
            outcome.cost_usd,
            outcome.result.is_synthetic,
        )

    def _stage_plan(
        self,
        source_text: str,
        question_text: str,
        analysis: dict | None,
        learner: LearnerContext,
        config: PipelineConfig,
    ):
        system = (
            "You are an instructional designer deciding how a specific explanation "
            "should be taught to a specific learner. Choose only the techniques this "
            "explanation actually needs. A short, already-clear explanation may need "
            "none of them, and saying so is a valid plan.\n\n" + GUARD_INSTRUCTION
        )
        user = "\n\n".join(
            [
                f"Question: {question_text}",
                f"Learner level: {learner.level}",
                f"Learner description: {learner.description}",
                f"Can be assumed to know: {learner.assumed_prior_knowledge}",
                f"Probably unfamiliar with: {learner.unfamiliar_with}",
                "Analysis of the source explanation:",
                json.dumps(analysis, indent=2) if analysis else "(not available)",
                "Source explanation:",
                untrusted_block("source_explanation", source_text),
                schema_instruction(PLAN_SCHEMA, "pedagogical_plan"),
            ]
        )
        data, outcome = call_structured(
            self.db,
            provider=config.provider,
            model_id=config.model_id,
            request=GenerationRequest(
                system=system,
                user=user,
                max_output_tokens=min(config.max_output_tokens, 3000),
                temperature=config.temperature,
                effort=config.effort,
                json_schema=PLAN_SCHEMA,
                json_schema_name="pedagogical_plan",
            ),
            purpose=CallPurpose.PLANNING,
            experiment_id=self.experiment_id,
        )
        return (
            data,
            self._record("B", "Pedagogical planning", outcome),
            outcome.cost_usd,
            outcome.result.is_synthetic,
        )

    def _stage_fidelity(
        self, source_text: str, transformed: str, treatments: list[str], config: PipelineConfig
    ):
        det = run_deterministic_checks(source_text, transformed, treatments)
        data, outcome = call_structured(
            self.db,
            provider=config.provider,
            model_id=config.model_id,
            request=GenerationRequest(
                system=FIDELITY_SYSTEM + "\n\n" + GUARD_INSTRUCTION,
                user=build_fidelity_user_prompt(
                    source_text, transformed, config.factual_checklist
                )
                + "\n\n"
                + schema_instruction(FIDELITY_SCHEMA, "fidelity_check"),
                max_output_tokens=min(config.max_output_tokens, 4000),
                temperature=config.temperature,
                effort=config.effort,
                json_schema=FIDELITY_SCHEMA,
                json_schema_name="fidelity_check",
            ),
            purpose=CallPurpose.FIDELITY,
            experiment_id=self.experiment_id,
        )

        llm_warnings = list(data.get("warnings") or [])
        for w in llm_warnings:
            w.setdefault("detector", "llm_reviewer")

        combined = det.warnings + llm_warnings
        drift = det.numeric_drift + list(data.get("numeric_drift") or [])

        # The deterministic layer can escalate the LLM's verdict but never
        # soften it: a model that says "clean" does not clear a numeric change.
        verdict = data.get("verdict", "clean")
        if any(w.get("severity") == "high" for w in combined):
            verdict = "serious_concerns"
        elif combined and verdict == "clean":
            verdict = "warnings"

        merged = {
            "verdict": verdict,
            "warnings": combined,
            "numeric_drift": drift,
            "preserved_claims": data.get("preserved_claims") or [],
            "checklist_coverage": data.get("checklist_coverage") or [],
            "notes": data.get("notes", ""),
            "llm_review_ran": True,
            "deterministic_warning_count": len(det.warnings),
            "llm_warning_count": len(llm_warnings),
            # Never render this as "verified correct".
            "provisional": True,
        }
        return (
            merged,
            self._record("D", "Fidelity verification", outcome),
            outcome.cost_usd,
            outcome.result.is_synthetic,
        )

    def _stage_concept_graph(self, source_text: str, question_text: str, config: PipelineConfig):
        system = (
            "You extract a concept dependency graph from a technical explanation. "
            "An edge A -> B means a reader must understand A before B makes sense. "
            "Only assert an edge you would defend; mark uncertain edges low "
            "confidence.\n\n" + GUARD_INSTRUCTION
        )
        user = "\n\n".join(
            [
                f"Question: {question_text}",
                "Explanation:",
                untrusted_block("explanation", source_text),
                schema_instruction(CONCEPT_GRAPH_SCHEMA, "concept_graph"),
            ]
        )
        data, outcome = call_structured(
            self.db,
            provider=config.provider,
            model_id=config.model_id,
            request=GenerationRequest(
                system=system,
                user=user,
                max_output_tokens=min(config.max_output_tokens, 3000),
                temperature=config.temperature,
                effort=config.effort,
                json_schema=CONCEPT_GRAPH_SCHEMA,
                json_schema_name="concept_graph",
            ),
            purpose=CallPurpose.CONCEPT_GRAPH,
            experiment_id=self.experiment_id,
        )
        return (
            data,
            self._record("Graph", "Concept dependency extraction", outcome),
            outcome.cost_usd,
            outcome.result.is_synthetic,
        )

    @staticmethod
    def _record(stage: str, label: str, outcome) -> StageRecord:
        return StageRecord(
            stage=stage,
            label=label,
            provider=outcome.result.provider,
            model_id=outcome.result.model_id,
            input_tokens=outcome.result.input_tokens,
            output_tokens=outcome.result.output_tokens,
            latency_ms=outcome.result.latency_ms,
            cost_usd=outcome.cost_usd,
            served_from_cache=outcome.result.served_from_cache,
            notes=list(outcome.result.control_limitations),
        )
