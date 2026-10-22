"""Pydantic request/response models.

Input limits live here so they are enforced at the boundary, before any text
reaches a prompt or the database.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import get_settings
from .enums import (
    EvalDimension,
    ExperimentType,
    ItemFormat,
    LearnerLevel,
    Provider,
)

MAX_TEXT = 24_000


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Questions and profiles
# ---------------------------------------------------------------------------


class QuestionCreate(BaseModel):
    text: str = Field(min_length=5, max_length=4000)
    domain: str = Field(default="general", max_length=120)
    topic: str = Field(default="", max_length=200)
    conceptual_difficulty: Literal["low", "moderate", "high", "unrated"] = "unrated"
    factual_checklist: list[str] = Field(default_factory=list, max_length=40)
    checklist_reviewed_by: str | None = Field(default=None, max_length=255)
    notes: str = Field(default="", max_length=8000)

    @field_validator("factual_checklist")
    @classmethod
    def _limit_claims(cls, value: list[str]) -> list[str]:
        return [v[:600] for v in value if v.strip()]


class QuestionUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=5, max_length=4000)
    domain: str | None = None
    topic: str | None = None
    conceptual_difficulty: Literal["low", "moderate", "high", "unrated"] | None = None
    factual_checklist: list[str] | None = None
    checklist_reviewed_by: str | None = None
    notes: str | None = None


class QuestionOut(ORMModel):
    id: str
    text: str
    domain: str
    topic: str
    conceptual_difficulty: str
    factual_checklist: list[str]
    checklist_reviewed_by: str | None
    notes: str
    is_seed: bool
    created_at: datetime


class LearnerProfileCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    level: LearnerLevel
    description: str = Field(default="", max_length=4000)
    assumed_prior_knowledge: list[str] = Field(default_factory=list, max_length=30)
    unfamiliar_with: list[str] = Field(default_factory=list, max_length=30)


class LearnerProfileOut(ORMModel):
    id: str
    name: str
    level: str
    description: str
    assumed_prior_knowledge: list[str]
    unfamiliar_with: list[str]
    is_builtin: bool


# ---------------------------------------------------------------------------
# Models and prompts
# ---------------------------------------------------------------------------


class ModelCatalogOut(ORMModel):
    id: str
    provider: str
    model_id: str
    display_name: str
    tier: str
    input_cost_per_mtok: float | None
    output_cost_per_mtok: float | None
    context_window: int | None
    supports_temperature: bool
    supports_effort: bool
    supports_max_output_tokens: bool
    supports_structured_output: bool
    default_effort: str | None
    is_enabled: bool
    verified_live: bool
    last_verified_at: datetime | None
    notes: str
    pricing_source: str


class ModelCatalogUpdate(BaseModel):
    is_enabled: bool | None = None
    input_cost_per_mtok: float | None = Field(default=None, ge=0)
    output_cost_per_mtok: float | None = Field(default=None, ge=0)
    supports_temperature: bool | None = None
    supports_effort: bool | None = None
    default_effort: str | None = None
    notes: str | None = Field(default=None, max_length=4000)


class PromptVersionOut(ORMModel):
    id: str
    version: int
    system_text: str
    user_template: str
    changelog: str
    is_active: bool
    created_at: datetime


class PromptTemplateOut(ORMModel):
    id: str
    key: str
    name: str
    condition: str
    description: str
    is_builtin: bool
    versions: list[PromptVersionOut]


class PromptTemplateCreate(BaseModel):
    key: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=2, max_length=200)
    condition: Literal["default", "generic_tutor", "structured_pedagogical", "custom"] = "custom"
    description: str = Field(default="", max_length=4000)
    system_text: str = Field(default="", max_length=MAX_TEXT)
    user_template: str = Field(default="{question}", max_length=MAX_TEXT)


class PromptVersionCreate(BaseModel):
    system_text: str = Field(default="", max_length=MAX_TEXT)
    user_template: str = Field(default="{question}", max_length=MAX_TEXT)
    changelog: str = Field(default="", max_length=2000)


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------


class ModelRefIn(BaseModel):
    provider: Provider
    model_id: str = Field(min_length=1, max_length=120)


class GenerationSettingsIn(BaseModel):
    max_output_tokens: int = Field(default=4096, ge=256, le=32_000)
    temperature: float | None = Field(default=None, ge=0, le=2)
    effort: Literal["low", "medium", "high", "xhigh", "max"] | None = None


class ExperimentSpecIn(BaseModel):
    name: str = Field(min_length=2, max_length=250)
    type: ExperimentType
    question_ids: list[str] = Field(min_length=1, max_length=30)
    source_models: list[ModelRefIn] = Field(min_length=1, max_length=6)
    prompt_template_keys: list[str] = Field(default_factory=list, max_length=8)
    treatment_sets: list[list[str]] = Field(default_factory=list, max_length=16)
    transform_models: list[ModelRefIn] = Field(default_factory=list, max_length=4)
    learner_profile_id: str | None = None
    base_prompt_key: str = "condition_a_default"
    generation_settings: GenerationSettingsIn = Field(default_factory=GenerationSettingsIn)
    transform_settings: GenerationSettingsIn = Field(default_factory=GenerationSettingsIn)
    objective: str = Field(default="", max_length=4000)
    hypothesis: str = Field(default="", max_length=4000)
    seed: int = Field(default=20261022, ge=0, le=2**31 - 1)
    repetitions: int = Field(default=1, ge=1, le=10)
    run_analysis: bool = True
    run_planning: bool = True
    run_fidelity: bool = True
    build_concept_graph: bool = False
    include_untransformed_control: bool = True


class ExperimentOut(ORMModel):
    id: str
    name: str
    type: str
    status: str
    objective: str
    hypothesis: str
    researcher_notes: str
    seed: int
    repetitions: int
    estimated_cost_usd: float
    config: dict
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class RunOut(ORMModel):
    id: str
    condition_id: str
    question_id: str
    replicate_index: int
    status: str
    attempts: int
    error: str | None
    error_type: str | None
    started_at: datetime | None
    finished_at: datetime | None


class ConditionOut(ORMModel):
    id: str
    label: str
    order_index: int
    provider: str
    model_id: str
    prompt_version_id: str | None
    learner_profile_id: str | None
    generation_settings: dict
    treatments: list[Any]
    transform_provider: str | None
    transform_model_id: str | None
    transform_settings: dict


class RunRequest(BaseModel):
    confirm_cost: bool = False
    retry_failed_only: bool = False


class JobOut(ORMModel):
    id: str
    kind: str
    status: str
    progress_done: int
    progress_total: int
    error: str | None
    experiment_id: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class ResponseOut(ORMModel):
    id: str
    kind: str
    origin: str
    run_id: str | None
    parent_response_id: str | None
    question_id: str | None
    learner_profile_id: str | None
    prompt_version_id: str | None
    provider: str
    model_id: str
    label: str
    text: str
    # The exact prompts this response was generated from. Exposed because
    # inspecting prompt configuration is a reproducibility requirement (§7);
    # these are the researcher's own templates, never a credential. Participant
    # payloads are built by a separate allow-list and never include them.
    system_prompt_snapshot: str
    user_prompt_snapshot: str
    applied_treatments: list[Any]
    control_limitations: list[Any]
    generation_settings: dict
    requested_settings: dict
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    cost_usd: float
    finish_reason: str | None
    served_from_cache: bool
    is_synthetic: bool
    created_at: datetime


class ResponseImport(BaseModel):
    """Manual import of a real ChatGPT / Claude web-chat answer.

    The brief is explicit that API output and consumer-interface output are not
    the same thing, so this path exists and records itself as distinct
    provenance.
    """

    question_id: str
    provider: Provider
    model_id: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=20, max_length=MAX_TEXT)
    label: str = Field(default="", max_length=250)
    interface: Literal["web_chat", "mobile_app", "other"] = "web_chat"
    captured_at: datetime | None = None
    learner_profile_id: str | None = None
    notes: str = Field(default="", max_length=4000)

    @field_validator("text")
    @classmethod
    def _limit(cls, value: str) -> str:
        limit = get_settings().max_input_chars
        if len(value) > limit:
            raise ValueError(f"Imported text exceeds the {limit} character limit.")
        return value


class AnnotationCreate(BaseModel):
    label: str = Field(default="", max_length=120)
    body: str = Field(default="", max_length=8000)
    quoted_excerpt: str = Field(default="", max_length=4000)
    author: str = Field(default="researcher", max_length=255)


class TransformRequest(BaseModel):
    treatments: list[str] = Field(min_length=1, max_length=6)
    provider: Provider
    model_id: str = Field(min_length=1, max_length=120)
    settings: GenerationSettingsIn = Field(default_factory=GenerationSettingsIn)
    run_analysis: bool = True
    run_planning: bool = True
    run_fidelity: bool = True
    treatment_order_override: list[str] | None = None
    save_variant: bool = True


class JudgeRequest(BaseModel):
    provider: Provider
    model_id: str = Field(min_length=1, max_length=120)
    effort: Literal["low", "medium", "high", "xhigh", "max"] | None = None
    response_ids: list[str] = Field(default_factory=list, max_length=100)


# ---------------------------------------------------------------------------
# Studies
# ---------------------------------------------------------------------------


class AssessmentItemIn(BaseModel):
    format: ItemFormat
    dimension: EvalDimension
    prompt: str = Field(min_length=5, max_length=4000)
    options: list[str] = Field(default_factory=list, max_length=8)
    correct_option_index: int | None = Field(default=None, ge=0, le=7)
    misconception_option_indexes: list[int] = Field(default_factory=list, max_length=8)
    rubric_key: str | None = None
    max_score: float = Field(default=1.0, ge=0, le=10)
    is_required: bool = True


class StudyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=250)
    question_id: str | None = None
    experiment_id: str | None = None
    response_ids: list[str] = Field(min_length=2, max_length=10)
    intro_text: str = Field(default="", max_length=8000)
    consent_text: str = Field(default="", max_length=8000)
    collect_prior_knowledge: bool = True
    seed: int = Field(default=20261022, ge=0, le=2**31 - 1)
    balance_conditions: bool = True
    max_per_condition: int | None = Field(default=None, ge=1, le=10_000)
    items: list[AssessmentItemIn] = Field(default_factory=list, max_length=30)


class ProxyRunIn(BaseModel):
    provider: Provider
    model_id: str = Field(min_length=1, max_length=120)


class StudyOut(ORMModel):
    id: str
    name: str
    status: str
    question_id: str | None
    experiment_id: str | None
    intro_text: str
    consent_text: str
    collect_prior_knowledge: bool
    seed: int
    balance_conditions: bool
    max_per_condition: int | None
    access_token: str
    created_at: datetime


class GradeIn(BaseModel):
    human_score: float = Field(ge=0, le=10)
    misconception_detected: bool = False
    grader_notes: str = Field(default="", max_length=4000)


# ---------------------------------------------------------------------------
# Participant-facing
# ---------------------------------------------------------------------------


class ParticipantEnter(BaseModel):
    participant_code: str | None = Field(default=None, max_length=32)
    consent_given: bool
    self_reported_level: LearnerLevel | None = None
    prior_knowledge: dict[str, Any] = Field(default_factory=dict)

    @field_validator("consent_given")
    @classmethod
    def _must_consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Participation requires consent.")
        return value


class ParticipantAnswer(BaseModel):
    item_id: str
    selected_option_index: int | None = Field(default=None, ge=0, le=7)
    text_answer: str = Field(default="", max_length=8000)
    likert_value: int | None = Field(default=None, ge=1, le=7)
    seconds_spent: float | None = Field(default=None, ge=0, le=86_400)


class ParticipantSubmit(BaseModel):
    participant_code: str = Field(min_length=3, max_length=32)
    answers: list[ParticipantAnswer] = Field(default_factory=list, max_length=40)
    reading_seconds: float | None = Field(default=None, ge=0, le=86_400)
    assessment_seconds: float | None = Field(default=None, ge=0, le=86_400)
    clarity_rating: int | None = Field(default=None, ge=1, le=7)
    cognitive_effort_rating: int | None = Field(default=None, ge=1, le=7)
    free_text_feedback: str = Field(default="", max_length=5000)
