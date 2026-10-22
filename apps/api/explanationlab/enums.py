"""Controlled vocabularies shared across the platform.

These are plain string enums so they serialise cleanly to JSON, into the
database, and into the generated TypeScript catalogue consumed by the web app.
"""

from __future__ import annotations

from enum import StrEnum


class Provider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MANUAL = "manual"


class ExperimentType(StrEnum):
    """The five experiments required by the research brief."""

    BASELINE = "baseline"  # Experiment 1
    PROMPT_INTERVENTION = "prompt_intervention"  # Experiment 2
    ABLATION = "ablation"  # Experiment 3
    CROSS_MODEL = "cross_model"  # Experiment 4
    HUMAN_STUDY = "human_study"  # Experiment 5


class ExperimentStatus(StrEnum):
    """Draft -> Configured -> Running -> Completed/Failed -> Evaluated -> Reported."""

    DRAFT = "draft"
    CONFIGURED = "configured"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    EVALUATED = "evaluated"
    REPORTED = "reported"


class ResponseKind(StrEnum):
    SOURCE = "source"
    TRANSFORMED = "transformed"


class ResponseOrigin(StrEnum):
    """Provenance. Demo fixtures are never silently mixed with real data."""

    API = "api"
    MANUAL_IMPORT = "manual_import"
    DEMO_FIXTURE = "demo_fixture"


class LearnerLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class PromptCondition(StrEnum):
    """Experiment 2's three required conditions."""

    DEFAULT = "default"  # Condition A
    GENERIC_TUTOR = "generic_tutor"  # Condition B
    STRUCTURED_PEDAGOGICAL = "structured_pedagogical"  # Condition C
    CUSTOM = "custom"


class Treatment(StrEnum):
    """Experiment 3's independently applicable transformation treatments."""

    T1_VOCABULARY = "T1"
    T2_SEQUENCING = "T2"
    T3_MECHANISM = "T3"
    T4_EXAMPLES = "T4"
    T5_STRUCTURE = "T5"
    T6_AUDIENCE = "T6"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobKind(StrEnum):
    EXPERIMENT_BATCH = "experiment_batch"
    TRANSFORMATION = "transformation"
    JUDGE_EVALUATION = "judge_evaluation"
    CONCEPT_GRAPH = "concept_graph"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class ItemFormat(StrEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ANSWER = "short_answer"
    SCENARIO = "scenario"
    LIKERT = "likert"


class EvalDimension(StrEnum):
    """Experiment 5's required evaluation dimensions."""

    IMMEDIATE_COMPREHENSION = "A_immediate_comprehension"
    MECHANISTIC_UNDERSTANDING = "B_mechanistic_understanding"
    TRANSFER = "C_transfer"
    PERCEIVED_CLARITY = "D_perceived_clarity"
    COGNITIVE_EFFORT = "E_cognitive_effort"
    MISCONCEPTION = "F_misconception"
    TIME = "G_time"
    DELAYED_RETENTION = "H_delayed_retention"


class GradingMode(StrEnum):
    MANUAL = "manual"
    AI_ASSISTED = "ai_assisted"
    AUTO_OBJECTIVE = "auto_objective"  # multiple-choice key matching


class StudyStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"


class AssignmentStatus(StrEnum):
    ASSIGNED = "assigned"
    CONSENTED = "consented"
    SUBMITTED = "submitted"
    WITHDRAWN = "withdrawn"


class EvidenceClass(StrEnum):
    """Keeps the four measurement categories separable everywhere they surface.

    The brief forbids collapsing these into one number; the type system is the
    cheapest place to enforce that.
    """

    AUTOMATED_DIAGNOSTIC = "automated_diagnostic"
    AI_JUDGE_OPINION = "ai_judge_opinion"
    HUMAN_PREFERENCE = "human_preference"
    HUMAN_COMPREHENSION = "human_comprehension"


class CallPurpose(StrEnum):
    GENERATION = "generation"
    TRANSFORMATION = "transformation"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    FIDELITY = "fidelity"
    JUDGE = "judge"
    CONCEPT_GRAPH = "concept_graph"
    GRADING = "grading"
