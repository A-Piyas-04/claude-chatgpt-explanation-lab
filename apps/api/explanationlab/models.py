"""Relational schema.

Two invariants the rest of the codebase relies on:

1. **Response rows are immutable.** Once written they are never updated. A
   transformation produces a *new* row pointing at its parent via
   ``parent_response_id``, so the full provenance chain from raw model output to
   final variant is always reconstructible.
2. **Synthetic provenance is sticky.** ``is_synthetic`` is copied onto every
   derived row (transformations, evaluations, usage records) so demo data can
   never be laundered into a real results table.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .enums import (
    AssignmentStatus,
    ExperimentStatus,
    ExperimentType,
    GradingMode,
    ItemFormat,
    JobKind,
    JobStatus,
    LearnerLevel,
    PromptCondition,
    Provider,
    ResponseKind,
    ResponseOrigin,
    RunStatus,
    StudyStatus,
)


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---------------------------------------------------------------------------
# People and audiences
# ---------------------------------------------------------------------------


class Researcher(Base, TimestampMixin):
    __tablename__ = "researchers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255))


class LearnerProfile(Base, TimestampMixin):
    """An audience specification. Also used as the T6 treatment parameter."""

    __tablename__ = "learner_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    level: Mapped[str] = mapped_column(String(32), default=LearnerLevel.INTERMEDIATE.value)
    description: Mapped[str] = mapped_column(Text, default="")
    assumed_prior_knowledge: Mapped[list] = mapped_column(JSON, default=list)
    unfamiliar_with: Mapped[list] = mapped_column(JSON, default=list)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------------------------------------------------------------------------
# Research questions
# ---------------------------------------------------------------------------


class ResearchQuestion(Base, TimestampMixin):
    __tablename__ = "research_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    text: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(120), default="general")
    topic: Mapped[str] = mapped_column(String(200), default="")
    # Conceptual difficulty is NOT assumed uniform across the bank.
    conceptual_difficulty: Mapped[str] = mapped_column(String(32), default="unrated")
    # Reviewed list of essential claims a correct explanation should contain.
    factual_checklist: Mapped[list] = mapped_column(JSON, default=list)
    checklist_reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    is_seed: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------------------------------------------------------------------------
# Models and providers
# ---------------------------------------------------------------------------


class ModelCatalogEntry(Base, TimestampMixin):
    """A selectable model plus its *capability record*.

    The capability flags exist because current frontier models reject
    parameters that older ones accepted (notably ``temperature``). Recording
    what a model does not support is how we keep experimental conditions
    honestly documented instead of silently divergent.
    """

    __tablename__ = "model_catalog"
    __table_args__ = (UniqueConstraint("provider", "model_id", name="uq_model_catalog_provider_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    provider: Mapped[str] = mapped_column(String(32))
    model_id: Mapped[str] = mapped_column(String(120))
    display_name: Mapped[str] = mapped_column(String(160))
    tier: Mapped[str] = mapped_column(String(32), default="standard")

    input_cost_per_mtok: Mapped[float | None] = mapped_column(Float, nullable=True)
    output_cost_per_mtok: Mapped[float | None] = mapped_column(Float, nullable=True)
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)

    supports_temperature: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_effort: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_max_output_tokens: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_structured_output: Mapped[bool] = mapped_column(Boolean, default=True)
    default_effort: Mapped[str | None] = mapped_column(String(16), nullable=True)

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    verified_live: Mapped[bool] = mapped_column(Boolean, default=False)
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str] = mapped_column(Text, default="")
    pricing_source: Mapped[str] = mapped_column(String(255), default="")


# ---------------------------------------------------------------------------
# Prompt templates (versioned)
# ---------------------------------------------------------------------------


class PromptTemplate(Base, TimestampMixin):
    __tablename__ = "prompt_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    key: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    condition: Mapped[str] = mapped_column(String(40), default=PromptCondition.CUSTOM.value)
    description: Mapped[str] = mapped_column(Text, default="")
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)

    versions: Mapped[list[PromptVersion]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="PromptVersion.version"
    )


class PromptVersion(Base, TimestampMixin):
    __tablename__ = "prompt_versions"
    __table_args__ = (UniqueConstraint("template_id", "version", name="uq_prompt_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    template_id: Mapped[str] = mapped_column(ForeignKey("prompt_templates.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    system_text: Mapped[str] = mapped_column(Text, default="")
    user_template: Mapped[str] = mapped_column(Text, default="{question}")
    changelog: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    template: Mapped[PromptTemplate] = relationship(back_populates="versions")


# ---------------------------------------------------------------------------
# Transformation strategies (versioned)
# ---------------------------------------------------------------------------


class TransformationStrategy(Base, TimestampMixin):
    __tablename__ = "transformation_strategies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    key: Mapped[str] = mapped_column(String(40), unique=True)  # T1..T6
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(80), default="")
    boundary_note: Mapped[str] = mapped_column(Text, default="")
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=True)

    versions: Mapped[list[TransformationVersion]] = relationship(
        back_populates="strategy",
        cascade="all, delete-orphan",
        order_by="TransformationVersion.version",
    )


class TransformationVersion(Base, TimestampMixin):
    __tablename__ = "transformation_versions"
    __table_args__ = (UniqueConstraint("strategy_id", "version", name="uq_transformation_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    strategy_id: Mapped[str] = mapped_column(
        ForeignKey("transformation_strategies.id", ondelete="CASCADE")
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    instruction_template: Mapped[str] = mapped_column(Text)
    input_schema: Mapped[dict] = mapped_column(JSON, default=dict)
    output_schema: Mapped[dict] = mapped_column(JSON, default=dict)
    default_params: Mapped[dict] = mapped_column(JSON, default=dict)
    changelog: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    strategy: Mapped[TransformationStrategy] = relationship(back_populates="versions")


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------


class Experiment(Base, TimestampMixin):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(250))
    type: Mapped[str] = mapped_column(String(40), default=ExperimentType.BASELINE.value)
    status: Mapped[str] = mapped_column(String(32), default=ExperimentStatus.DRAFT.value)
    objective: Mapped[str] = mapped_column(Text, default="")
    hypothesis: Mapped[str] = mapped_column(Text, default="")
    researcher_notes: Mapped[str] = mapped_column(Text, default="")
    seed: Mapped[int] = mapped_column(Integer, default=20261022)
    repetitions: Mapped[int] = mapped_column(Integer, default=1)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    conditions: Mapped[list[ExperimentCondition]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )
    runs: Mapped[list[ExperimentRun]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )
    questions: Mapped[list[ExperimentQuestion]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )


class ExperimentQuestion(Base):
    """Matched question set for an experiment."""

    __tablename__ = "experiment_questions"
    __table_args__ = (UniqueConstraint("experiment_id", "question_id", name="uq_experiment_question"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    question_id: Mapped[str] = mapped_column(ForeignKey("research_questions.id"))
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    experiment: Mapped[Experiment] = relationship(back_populates="questions")
    question: Mapped[ResearchQuestion] = relationship()


class ExperimentCondition(Base, TimestampMixin):
    """One experimental cell: who generates, with what prompt, under what treatments."""

    __tablename__ = "experiment_conditions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(200))
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    # Source generation
    provider: Mapped[str] = mapped_column(String(32), default=Provider.OPENAI.value)
    model_id: Mapped[str] = mapped_column(String(120), default="")
    prompt_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("prompt_versions.id"), nullable=True
    )
    learner_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("learner_profiles.id"), nullable=True
    )
    generation_settings: Mapped[dict] = mapped_column(JSON, default=dict)

    # Transformation (Experiments 3 and 4). Deliberately configured separately
    # from the source model so methodology and transformer are separable.
    treatments: Mapped[list] = mapped_column(JSON, default=list)
    transform_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    transform_model_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    transform_settings: Mapped[dict] = mapped_column(JSON, default=dict)

    # For cross-model experiments reusing an existing answer as the source.
    source_response_id: Mapped[str | None] = mapped_column(
        ForeignKey("responses.id"), nullable=True
    )

    experiment: Mapped[Experiment] = relationship(back_populates="conditions")
    prompt_version: Mapped[PromptVersion | None] = relationship()
    learner_profile: Mapped[LearnerProfile | None] = relationship()


class ExperimentRun(Base, TimestampMixin):
    """One (condition x question x replicate) unit of work. Retryable."""

    __tablename__ = "experiment_runs"
    __table_args__ = (
        UniqueConstraint(
            "condition_id", "question_id", "replicate_index", name="uq_run_cell"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    condition_id: Mapped[str] = mapped_column(
        ForeignKey("experiment_conditions.id", ondelete="CASCADE")
    )
    question_id: Mapped[str] = mapped_column(ForeignKey("research_questions.id"))
    replicate_index: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(String(32), default=RunStatus.PENDING.value)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    experiment: Mapped[Experiment] = relationship(back_populates="runs")
    condition: Mapped[ExperimentCondition] = relationship()
    question: Mapped[ResearchQuestion] = relationship()
    responses: Mapped[list[Response]] = relationship(back_populates="run")


# ---------------------------------------------------------------------------
# Responses (immutable)
# ---------------------------------------------------------------------------


class Response(Base, TimestampMixin):
    """A raw or transformed explanation, plus everything needed to reproduce it."""

    __tablename__ = "responses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String(24), default=ResponseKind.SOURCE.value)
    origin: Mapped[str] = mapped_column(String(24), default=ResponseOrigin.API.value)

    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("experiment_runs.id", ondelete="SET NULL"), nullable=True
    )
    parent_response_id: Mapped[str | None] = mapped_column(
        ForeignKey("responses.id"), nullable=True
    )
    question_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_questions.id"), nullable=True
    )
    learner_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("learner_profiles.id"), nullable=True
    )
    prompt_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("prompt_versions.id"), nullable=True
    )

    # Provenance
    provider: Mapped[str] = mapped_column(String(32))
    model_id: Mapped[str] = mapped_column(String(120), default="")
    label: Mapped[str] = mapped_column(String(250), default="")

    # Exact inputs, snapshotted so a later template edit cannot rewrite history.
    system_prompt_snapshot: Mapped[str] = mapped_column(Text, default="")
    user_prompt_snapshot: Mapped[str] = mapped_column(Text, default="")
    generation_settings: Mapped[dict] = mapped_column(JSON, default=dict)
    requested_settings: Mapped[dict] = mapped_column(JSON, default=dict)
    control_limitations: Mapped[list] = mapped_column(JSON, default=list)

    text: Mapped[str] = mapped_column(Text)

    # Transformation metadata
    applied_treatments: Mapped[list] = mapped_column(JSON, default=list)
    transformation_version_ids: Mapped[list] = mapped_column(JSON, default=list)
    transformation_meta: Mapped[dict] = mapped_column(JSON, default=dict)

    # Accounting
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    finish_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    served_from_cache: Mapped[bool] = mapped_column(Boolean, default=False)

    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)

    run: Mapped[ExperimentRun | None] = relationship(back_populates="responses")
    parent: Mapped[Response | None] = relationship(remote_side=[id])
    question: Mapped[ResearchQuestion | None] = relationship()
    learner_profile: Mapped[LearnerProfile | None] = relationship()


class ResponseCache(Base, TimestampMixin):
    """Deterministic-request cache so re-analysis does not re-bill the operator."""

    __tablename__ = "response_cache"

    request_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32))
    model_id: Mapped[str] = mapped_column(String(120))
    text: Mapped[str] = mapped_column(Text)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finish_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)


class Annotation(Base, TimestampMixin):
    """Manual researcher annotation of explanation characteristics."""

    __tablename__ = "annotations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    response_id: Mapped[str] = mapped_column(ForeignKey("responses.id", ondelete="CASCADE"))
    author: Mapped[str] = mapped_column(String(255), default="researcher")
    label: Mapped[str] = mapped_column(String(120), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    quoted_excerpt: Mapped[str] = mapped_column(Text, default="")


# ---------------------------------------------------------------------------
# Analysis artefacts
# ---------------------------------------------------------------------------


class ConceptGraph(Base, TimestampMixin):
    """An LLM-inferred prerequisite graph. Always a hypothesis, never ground truth."""

    __tablename__ = "concept_graphs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    response_id: Mapped[str] = mapped_column(ForeignKey("responses.id", ondelete="CASCADE"))
    nodes: Mapped[list] = mapped_column(JSON, default=list)
    edges: Mapped[list] = mapped_column(JSON, default=list)
    teaching_order: Mapped[list] = mapped_column(JSON, default=list)
    cycles_detected: Mapped[list] = mapped_column(JSON, default=list)
    provider: Mapped[str] = mapped_column(String(32), default="")
    model_id: Mapped[str] = mapped_column(String(120), default="")
    is_hypothesis: Mapped[bool] = mapped_column(Boolean, default=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)


class TextMetrics(Base, TimestampMixin):
    """Deterministic surface diagnostics. Not a measure of understanding."""

    __tablename__ = "text_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    response_id: Mapped[str] = mapped_column(
        ForeignKey("responses.id", ondelete="CASCADE"), unique=True
    )
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics_version: Mapped[str] = mapped_column(String(32), default="1.0")


class JudgeEvaluation(Base, TimestampMixin):
    """A judge model's provisional opinion. Explicitly not comprehension evidence."""

    __tablename__ = "judge_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    response_id: Mapped[str] = mapped_column(ForeignKey("responses.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(32))
    model_id: Mapped[str] = mapped_column(String(120))
    rubric_key: Mapped[str] = mapped_column(String(80), default="explanation_quality")
    rubric_version: Mapped[int] = mapped_column(Integer, default=1)
    blinded: Mapped[bool] = mapped_column(Boolean, default=True)
    presentation_order: Mapped[list] = mapped_column(JSON, default=list)
    scores: Mapped[list] = mapped_column(JSON, default=list)
    overall_notes: Mapped[str] = mapped_column(Text, default="")
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)


class FidelityReport(Base, TimestampMixin):
    """Stage D output. A provisional assessment, not proof of correctness."""

    __tablename__ = "fidelity_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    response_id: Mapped[str] = mapped_column(ForeignKey("responses.id", ondelete="CASCADE"))
    source_response_id: Mapped[str] = mapped_column(ForeignKey("responses.id"))
    provider: Mapped[str] = mapped_column(String(32), default="")
    model_id: Mapped[str] = mapped_column(String(120), default="")
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    checklist_coverage: Mapped[list] = mapped_column(JSON, default=list)
    verdict: Mapped[str] = mapped_column(String(40), default="unreviewed")
    numeric_drift: Mapped[list] = mapped_column(JSON, default=list)
    reviewed_by_human: Mapped[bool] = mapped_column(Boolean, default=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------------------------------------------------------------------------
# Human studies
# ---------------------------------------------------------------------------


class GradingRubric(Base, TimestampMixin):
    __tablename__ = "grading_rubrics"
    __table_args__ = (UniqueConstraint("key", "version", name="uq_rubric_key_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    key: Mapped[str] = mapped_column(String(80))
    version: Mapped[int] = mapped_column(Integer, default=1)
    name: Mapped[str] = mapped_column(String(200))
    criteria: Mapped[list] = mapped_column(JSON, default=list)
    max_score: Mapped[float] = mapped_column(Float, default=1.0)


class Study(Base, TimestampMixin):
    __tablename__ = "studies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(250))
    status: Mapped[str] = mapped_column(String(24), default=StudyStatus.DRAFT.value)
    question_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_questions.id"), nullable=True
    )
    experiment_id: Mapped[str | None] = mapped_column(
        ForeignKey("experiments.id", ondelete="SET NULL"), nullable=True
    )
    intro_text: Mapped[str] = mapped_column(Text, default="")
    consent_text: Mapped[str] = mapped_column(Text, default="")
    audience_criteria: Mapped[dict] = mapped_column(JSON, default=dict)
    collect_prior_knowledge: Mapped[bool] = mapped_column(Boolean, default=True)
    seed: Mapped[int] = mapped_column(Integer, default=20261022)
    balance_conditions: Mapped[bool] = mapped_column(Boolean, default=True)
    max_per_condition: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Unguessable participant token. Grants assessment access only, never
    # researcher controls.
    access_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    conditions: Mapped[list[StudyCondition]] = relationship(
        back_populates="study", cascade="all, delete-orphan"
    )
    items: Mapped[list[AssessmentItem]] = relationship(
        back_populates="study", cascade="all, delete-orphan", order_by="AssessmentItem.order_index"
    )


class StudyCondition(Base, TimestampMixin):
    """One blinded arm: a specific response variant shown to participants."""

    __tablename__ = "study_conditions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    study_id: Mapped[str] = mapped_column(ForeignKey("studies.id", ondelete="CASCADE"))
    # Researcher-facing label only. Never sent to a participant.
    label: Mapped[str] = mapped_column(String(200))
    response_id: Mapped[str] = mapped_column(ForeignKey("responses.id"))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    study: Mapped[Study] = relationship(back_populates="conditions")
    response: Mapped[Response] = relationship()


class AssessmentItem(Base, TimestampMixin):
    __tablename__ = "assessment_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    study_id: Mapped[str] = mapped_column(ForeignKey("studies.id", ondelete="CASCADE"))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    format: Mapped[str] = mapped_column(String(32), default=ItemFormat.MULTIPLE_CHOICE.value)
    dimension: Mapped[str] = mapped_column(String(48))
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON, default=list)
    correct_option_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # A distractor index that indicates a specific misconception, if any.
    misconception_option_indexes: Mapped[list] = mapped_column(JSON, default=list)
    rubric_id: Mapped[str | None] = mapped_column(ForeignKey("grading_rubrics.id"), nullable=True)
    max_score: Mapped[float] = mapped_column(Float, default=1.0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)

    study: Mapped[Study] = relationship(back_populates="items")
    rubric: Mapped[GradingRubric | None] = relationship()


class StudyAssignment(Base, TimestampMixin):
    __tablename__ = "study_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    study_id: Mapped[str] = mapped_column(ForeignKey("studies.id", ondelete="CASCADE"))
    condition_id: Mapped[str] = mapped_column(ForeignKey("study_conditions.id"))
    # Anonymous participant identifier. No personal information is collected.
    participant_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default=AssignmentStatus.ASSIGNED.value)
    prior_knowledge: Mapped[dict] = mapped_column(JSON, default=dict)
    self_reported_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    item_order: Mapped[list] = mapped_column(JSON, default=list)
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    condition: Mapped[StudyCondition] = relationship()


class ParticipantSubmission(Base, TimestampMixin):
    __tablename__ = "participant_submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    assignment_id: Mapped[str] = mapped_column(
        ForeignKey("study_assignments.id", ondelete="CASCADE"), unique=True
    )
    reading_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    assessment_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    clarity_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cognitive_effort_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    free_text_feedback: Mapped[str] = mapped_column(Text, default="")

    assignment: Mapped[StudyAssignment] = relationship()
    item_responses: Mapped[list[ItemResponse]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class ItemResponse(Base, TimestampMixin):
    __tablename__ = "item_responses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("participant_submissions.id", ondelete="CASCADE")
    )
    item_id: Mapped[str] = mapped_column(ForeignKey("assessment_items.id"))
    selected_option_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text_answer: Mapped[str] = mapped_column(Text, default="")
    likert_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seconds_spent: Mapped[float | None] = mapped_column(Float, nullable=True)
    presented_order: Mapped[int] = mapped_column(Integer, default=0)

    # Scores are kept apart so an AI grade can never overwrite a human one.
    auto_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_suggested_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_rationale: Mapped[str] = mapped_column(Text, default="")
    human_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    grading_mode: Mapped[str] = mapped_column(String(32), default=GradingMode.MANUAL.value)
    rubric_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    misconception_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    grader_notes: Mapped[str] = mapped_column(Text, default="")

    submission: Mapped[ParticipantSubmission] = relationship(back_populates="item_responses")
    item: Mapped[AssessmentItem] = relationship()

    @property
    def final_score(self) -> float | None:
        """Human judgement wins; objective auto-scores next; AI never silently wins."""
        if self.human_score is not None:
            return self.human_score
        if self.auto_score is not None:
            return self.auto_score
        return None


# ---------------------------------------------------------------------------
# Operations: usage, jobs, reports
# ---------------------------------------------------------------------------


class UsageRecord(Base, TimestampMixin):
    __tablename__ = "usage_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    provider: Mapped[str] = mapped_column(String(32))
    model_id: Mapped[str] = mapped_column(String(120), default="")
    purpose: Mapped[str] = mapped_column(String(40))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    served_from_cache: Mapped[bool] = mapped_column(Boolean, default=False)
    experiment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    response_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)


class Job(Base, TimestampMixin):
    """Durable background work. Survives a restart; retries without duplicating."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String(40), default=JobKind.EXPERIMENT_BATCH.value)
    status: Mapped[str] = mapped_column(String(24), default=JobStatus.QUEUED.value, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    experiment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1)
    progress_done: Mapped[int] = mapped_column(Integer, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Guards against accidental duplicate submission of the same work.
    idempotency_key: Mapped[str | None] = mapped_column(
        String(120), nullable=True, unique=True, index=True
    )


class ResearchReport(Base, TimestampMixin):
    __tablename__ = "research_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(250))
    kind: Mapped[str] = mapped_column(String(40), default="experiment")
    experiment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    study_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    body_markdown: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    contains_synthetic_data: Mapped[bool] = mapped_column(Boolean, default=False)
