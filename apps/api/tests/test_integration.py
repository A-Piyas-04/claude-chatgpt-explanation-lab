"""Integration tests: experiment creation, provider adapters (mocked),
persistence, transformation pipeline, evaluation persistence, study
submissions, report generation."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from explanationlab.enums import CallPurpose, ResponseKind, RunStatus
from explanationlab.gateway import (
    SpendCapExceeded,
    StructuredOutputError,
    call_model,
    extract_json,
)
from explanationlab.models import (
    ExperimentRun,
    JudgeEvaluation,
    Response,
    ResponseCache,
    TextMetrics,
    UsageRecord,
)
from explanationlab.providers.base import (
    BaseProvider,
    GenerationRequest,
    GenerationResult,
    ModelCapabilities,
    ProviderError,
)

# ---------------------------------------------------------------------------
# Mock provider adapters
# ---------------------------------------------------------------------------


class MockProvider(BaseProvider):
    """Records calls and returns scripted text. No network."""

    def __init__(self, texts=None, fail_with=None):
        self.calls: list[tuple[str, GenerationRequest]] = []
        self.texts = list(texts or ["Mock explanation about caching."])
        self.fail_with = fail_with

    def capabilities(self, model_id: str) -> ModelCapabilities:
        return ModelCapabilities(supports_temperature=True, supports_effort=True)

    def generate(self, model_id: str, request: GenerationRequest) -> GenerationResult:
        self.calls.append((model_id, request))
        if self.fail_with:
            raise self.fail_with
        text = self.texts[min(len(self.calls) - 1, len(self.texts) - 1)]
        return GenerationResult(
            text=text,
            provider="openai",
            model_id=model_id,
            input_tokens=100,
            output_tokens=200,
            latency_ms=42,
            finish_reason="end_turn",
        )


@pytest.fixture
def mock_provider(monkeypatch):
    provider = MockProvider()

    def _get(_name, allow_demo=True):
        return provider

    monkeypatch.setattr("explanationlab.gateway.get_provider", _get)
    return provider


# ---------------------------------------------------------------------------
# Gateway: accounting, caching, errors
# ---------------------------------------------------------------------------


def test_call_model_records_usage_and_cost(db, mock_provider):
    before = db.execute(select(UsageRecord)).scalars().all()

    outcome = call_model(
        db,
        provider="openai",
        model_id="gpt-6.1-sol",
        request=GenerationRequest(system="s", user="u"),
        purpose=CallPurpose.GENERATION,
    )
    db.commit()

    assert outcome.result.text == "Mock explanation about caching."
    # gpt-6.1-sol is $2/$10 per MTok: 100 in + 200 out.
    expected = (100 / 1_000_000) * 2.0 + (200 / 1_000_000) * 10.0
    assert outcome.cost_usd == pytest.approx(expected, rel=1e-6)

    after = db.execute(select(UsageRecord)).scalars().all()
    assert len(after) == len(before) + 1
    record = db.get(UsageRecord, outcome.usage_record_id)
    assert record.success is True
    assert record.purpose == CallPurpose.GENERATION.value
    assert record.input_tokens == 100


def test_provider_failure_is_recorded_then_raised(db, monkeypatch):
    failing = MockProvider(fail_with=ProviderError("boom", error_type="rate_limit"))
    monkeypatch.setattr("explanationlab.gateway.get_provider", lambda *_a, **_k: failing)

    with pytest.raises(ProviderError, match="boom"):
        call_model(
            db,
            provider="openai",
            model_id="gpt-6.1-sol",
            request=GenerationRequest(system="s", user="u"),
            purpose=CallPurpose.GENERATION,
        )
    db.commit()

    record = db.execute(
        select(UsageRecord)
        .where(UsageRecord.success.is_(False))
        .order_by(UsageRecord.created_at.desc())
    ).scalars().first()
    assert record is not None
    assert record.error_type == "rate_limit"
    assert "boom" in record.error_message


def test_cache_reuse_is_free_and_labelled(db, mock_provider, monkeypatch):
    monkeypatch.setattr(
        "explanationlab.gateway.get_settings",
        lambda: _settings_with(enable_response_cache=True),
    )
    request = GenerationRequest(system="cache-test", user="unique-user-prompt")

    first = call_model(
        db,
        provider="openai",
        model_id="gpt-6.1-sol",
        request=request,
        purpose=CallPurpose.GENERATION,
    )
    db.commit()
    assert first.result.served_from_cache is False
    assert first.cost_usd > 0
    assert len(mock_provider.calls) == 1

    second = call_model(
        db,
        provider="openai",
        model_id="gpt-6.1-sol",
        request=request,
        purpose=CallPurpose.GENERATION,
    )
    db.commit()
    # No second provider call, no second charge, and the reuse is declared.
    assert len(mock_provider.calls) == 1
    assert second.result.served_from_cache is True
    assert second.cost_usd == 0.0
    assert any("cache" in note.lower() for note in second.result.control_limitations)

    cached = db.get(ResponseCache, request.cache_key("openai", "gpt-6.1-sol"))
    assert cached.hit_count == 1


def test_spend_cap_blocks_further_calls(db, mock_provider, monkeypatch):
    monkeypatch.setattr(
        "explanationlab.gateway.get_settings", lambda: _settings_with(daily_spend_cap_usd=0.0)
    )
    monkeypatch.setattr("explanationlab.gateway.spend_today", lambda _db: 5.0)

    with pytest.raises(SpendCapExceeded, match="Daily spend cap"):
        call_model(
            db,
            provider="openai",
            model_id="gpt-6.1-sol",
            request=GenerationRequest(system="s", user="u"),
            purpose=CallPurpose.GENERATION,
        )


def _settings_with(**overrides):
    from explanationlab.config import get_settings

    base = get_settings()
    data = base.model_dump()
    data.update(overrides)
    return type(base)(**data)


def test_extract_json_tolerates_wrappers():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 2}\n```') == {"a": 2}
    assert extract_json('Sure, here it is:\n{"a": 3}\nHope that helps!') == {"a": 3}
    with pytest.raises(StructuredOutputError):
        extract_json("no json at all")


# ---------------------------------------------------------------------------
# Experiment creation and persistence
# ---------------------------------------------------------------------------


def test_experiment_creation_materialises_conditions_and_runs(db, question):
    from explanationlab.experiments.orchestrator import (
        ExperimentSpec,
        ModelRef,
        create_experiment,
    )

    spec = ExperimentSpec(
        name="Integration baseline",
        type="baseline",
        question_ids=[question.id],
        source_models=[
            ModelRef("openai", "gpt-6.1-sol"),
            ModelRef("anthropic", "claude-sonnet-5-5"),
        ],
        repetitions=2,
    )
    experiment, projection = create_experiment(db, spec)
    db.commit()

    assert experiment.status == "configured"
    assert len(experiment.conditions) == 2
    # 2 conditions x 1 question x 2 replicates
    runs = db.execute(
        select(ExperimentRun).where(ExperimentRun.experiment_id == experiment.id)
    ).scalars().all()
    assert len(runs) == 4
    assert projection["total_model_calls"] == 4
    assert all(r.status == RunStatus.PENDING.value for r in runs)
    # The prompt-guard deviation is recorded in the config.
    assert "prompt_guard_note" in experiment.config


def test_batch_ceiling_refuses_oversized_configuration(db, monkeypatch):
    from sqlalchemy import select as sa_select

    from explanationlab.experiments import orchestrator
    from explanationlab.models import ResearchQuestion

    monkeypatch.setattr(
        orchestrator, "get_settings", lambda: _settings_with(max_batch_requests=3)
    )
    questions = db.execute(sa_select(ResearchQuestion).limit(10)).scalars().all()
    spec = orchestrator.ExperimentSpec(
        name="too big",
        type="baseline",
        question_ids=[q.id for q in questions],
        source_models=[orchestrator.ModelRef("openai", "gpt-6.1-sol")],
    )
    with pytest.raises(orchestrator.ConfigurationError, match="over the limit"):
        orchestrator.create_experiment(db, spec)


def test_run_execution_persists_response_and_diagnostics(db, question, mock_provider):
    from explanationlab.experiments.orchestrator import (
        ExperimentSpec,
        ModelRef,
        create_experiment,
        execute_run,
    )

    experiment, _ = create_experiment(
        db,
        ExperimentSpec(
            name="Execution test",
            type="baseline",
            question_ids=[question.id],
            source_models=[ModelRef("openai", "gpt-6.1-sol")],
        ),
    )
    db.commit()
    run = db.execute(
        select(ExperimentRun).where(ExperimentRun.experiment_id == experiment.id)
    ).scalars().first()

    response = execute_run(db, run)
    db.commit()

    assert run.status == RunStatus.SUCCEEDED.value
    assert response.kind == ResponseKind.SOURCE.value
    assert response.text == "Mock explanation about caching."
    # The exact prompts are snapshotted for reproducibility.
    assert response.user_prompt_snapshot
    assert "<untrusted_content" in response.user_prompt_snapshot
    # Diagnostics are computed automatically.
    metrics = db.execute(
        select(TextMetrics).where(TextMetrics.response_id == response.id)
    ).scalar_one()
    assert metrics.metrics["surface"]["word_count"] > 0


def test_rerunning_a_succeeded_run_does_not_duplicate_work(db, question, mock_provider):
    from explanationlab.experiments.orchestrator import (
        ExperimentSpec,
        ModelRef,
        create_experiment,
        execute_run,
    )

    experiment, _ = create_experiment(
        db,
        ExperimentSpec(
            name="Idempotency test",
            type="baseline",
            question_ids=[question.id],
            source_models=[ModelRef("openai", "gpt-6.1-sol")],
        ),
    )
    db.commit()
    run = db.execute(
        select(ExperimentRun).where(ExperimentRun.experiment_id == experiment.id)
    ).scalars().first()

    first = execute_run(db, run)
    db.commit()
    calls_after_first = len(mock_provider.calls)

    second = execute_run(db, run)
    db.commit()

    assert second.id == first.id
    assert len(mock_provider.calls) == calls_after_first, "no second provider call"


def test_failed_run_records_error_and_can_be_retried(db, question, monkeypatch):
    from explanationlab.experiments.orchestrator import (
        ExperimentSpec,
        ModelRef,
        create_experiment,
        execute_run,
    )

    failing = MockProvider(fail_with=ProviderError("upstream down", error_type="server_error"))
    monkeypatch.setattr("explanationlab.gateway.get_provider", lambda *_a, **_k: failing)

    experiment, _ = create_experiment(
        db,
        ExperimentSpec(
            name="Failure test",
            type="baseline",
            question_ids=[question.id],
            source_models=[ModelRef("openai", "gpt-6.1-sol")],
        ),
    )
    db.commit()
    run = db.execute(
        select(ExperimentRun).where(ExperimentRun.experiment_id == experiment.id)
    ).scalars().first()

    with pytest.raises(ProviderError):
        execute_run(db, run)
    db.commit()

    assert run.status == RunStatus.FAILED.value
    assert run.error_type == "server_error"
    assert "upstream down" in run.error
    assert run.attempts == 1

    # Retry with a working provider succeeds and increments attempts.
    working = MockProvider()
    monkeypatch.setattr("explanationlab.gateway.get_provider", lambda *_a, **_k: working)
    execute_run(db, run)
    db.commit()
    assert run.status == RunStatus.SUCCEEDED.value
    assert run.attempts == 2


# ---------------------------------------------------------------------------
# Transformation pipeline
# ---------------------------------------------------------------------------


def test_transformation_pipeline_applies_treatments_sequentially(db, monkeypatch):
    """Each treatment must see the previous treatment's output."""
    import json

    from explanationlab.transformations.base import (
        ANALYSIS_SCHEMA,
        FIDELITY_SCHEMA,
        PLAN_SCHEMA,
    )
    from explanationlab.transformations.pipeline import (
        LearnerContext,
        PipelineConfig,
        TransformationPipeline,
    )

    class ScriptedProvider(BaseProvider):
        def __init__(self):
            self.prompts: list[str] = []

        def capabilities(self, model_id):
            return ModelCapabilities()

        def generate(self, model_id, request):
            self.prompts.append(request.user)
            if request.json_schema is ANALYSIS_SCHEMA:
                body = json.dumps(
                    {
                        "main_topic": "caching",
                        "primary_claims": ["a cache avoids a query"],
                        "key_concepts": ["cache"],
                        "prerequisite_concepts": ["query cost"],
                        "technical_vocabulary": [
                            {"term": "eviction", "explained_in_text": False}
                        ],
                    }
                )
            elif request.json_schema is PLAN_SCHEMA:
                body = json.dumps(
                    {
                        "learner_level": "intermediate",
                        "learning_objectives": ["explain reuse"],
                        "prerequisite_order": ["query cost", "cache"],
                        "explanation_sequence": ["motivate", "mechanism"],
                        "needs_concrete_example": True,
                        "needs_analogy": False,
                        "needs_diagram": False,
                        "detail_level": "moderate",
                    }
                )
            elif request.json_schema is FIDELITY_SCHEMA:
                body = json.dumps({"verdict": "clean", "warnings": []})
            elif "T1" in request.user or "reduce the effort of reading" in request.user:
                body = "STAGE1 output text about caching."
            else:
                body = "STAGE2 output text about caching."
            return GenerationResult(
                text=body,
                provider="openai",
                model_id=model_id,
                input_tokens=50,
                output_tokens=60,
                latency_ms=10,
            )

    scripted = ScriptedProvider()
    monkeypatch.setattr("explanationlab.gateway.get_provider", lambda *_a, **_k: scripted)

    pipeline = TransformationPipeline(db)
    result = pipeline.run(
        source_text="Original dense text about caching with numbers 200ms and 5ms.",
        question_text="How does caching work?",
        learner=LearnerContext(level="intermediate"),
        config=PipelineConfig(
            treatments=["T1", "T5"],
            provider="openai",
            model_id="gpt-6.1-sol",
        ),
    )
    db.commit()

    assert result.applied_treatments == ["T1", "T5"]
    assert result.analysis["main_topic"] == "caching"
    assert result.plan["needs_analogy"] is False
    assert len(result.changes) == 2
    # T5 received T1's output, not the original.
    assert result.changes[1].text_before == "STAGE1 output text about caching."
    assert result.text == "STAGE2 output text about caching."
    # Stage records cover A, B, two treatments and D.
    assert [s.stage for s in result.stages] == ["A", "B", "C", "C", "D"]


def test_deterministic_checks_escalate_a_clean_llm_verdict(db, monkeypatch):
    """An LLM saying 'clean' must not clear a numeric change."""
    import json

    from explanationlab.transformations.base import FIDELITY_SCHEMA
    from explanationlab.transformations.pipeline import (
        LearnerContext,
        PipelineConfig,
        TransformationPipeline,
    )

    class DriftingProvider(BaseProvider):
        def capabilities(self, model_id):
            return ModelCapabilities()

        def generate(self, model_id, request):
            if request.json_schema is FIDELITY_SCHEMA:
                text = json.dumps({"verdict": "clean", "warnings": []})
            elif request.json_schema is not None:
                text = json.dumps({})
            else:
                # Silently changes 200ms to 900ms.
                text = "Rewritten text where latency is 900ms instead."
            return GenerationResult(
                text=text, provider="openai", model_id=model_id, input_tokens=5, output_tokens=5
            )

    monkeypatch.setattr(
        "explanationlab.gateway.get_provider", lambda *_a, **_k: DriftingProvider()
    )

    pipeline = TransformationPipeline(db)
    result = pipeline.run(
        source_text="Latency is 200ms under load.",
        question_text="q",
        learner=LearnerContext(),
        config=PipelineConfig(
            treatments=["T1"],
            provider="openai",
            model_id="gpt-6.1-sol",
            run_analysis=False,
            run_planning=False,
        ),
    )
    db.commit()

    assert result.fidelity["verdict"] == "serious_concerns"
    assert result.fidelity["numeric_drift"]
    assert result.fidelity["provisional"] is True
    assert any(w["type"] == "numeric_change" for w in result.fidelity["warnings"])
    assert result.fidelity["deterministic_warning_count"] >= 1


def test_pipeline_rejects_empty_treatment_list(db):
    from explanationlab.transformations.pipeline import (
        LearnerContext,
        PipelineConfig,
        TransformationPipeline,
    )

    with pytest.raises(ValueError, match="No valid treatments"):
        TransformationPipeline(db).run(
            source_text="x",
            question_text="q",
            learner=LearnerContext(),
            config=PipelineConfig(treatments=[], provider="openai", model_id="gpt-6.1-sol"),
        )


# ---------------------------------------------------------------------------
# Evaluation persistence
# ---------------------------------------------------------------------------


def test_judge_evaluation_persists_blinded_and_inherits_synthetic_flag(db, question, monkeypatch):
    import json

    from explanationlab.evaluation.judge import judge_response

    payload = {
        "scores": [
            {
                "metric": "clarity",
                "score": 4,
                "rationale": "clear enough",
                "evidence": "a quoted span",
                "confidence": "medium",
            }
        ],
        "overall_notes": "fine",
    }

    class JudgeProvider(BaseProvider):
        def __init__(self):
            self.saw: list[str] = []

        def capabilities(self, model_id):
            return ModelCapabilities()

        def generate(self, model_id, request):
            self.saw.append(request.user + request.system)
            return GenerationResult(
                text=json.dumps(payload),
                provider="openai",
                model_id=model_id,
                input_tokens=10,
                output_tokens=20,
            )

    judge = JudgeProvider()
    monkeypatch.setattr("explanationlab.gateway.get_provider", lambda *_a, **_k: judge)

    response = Response(
        kind=ResponseKind.SOURCE.value,
        provider="anthropic",
        model_id="claude-sonnet-5-5",
        question_id=question.id,
        text="An explanation about caching.",
        is_synthetic=True,
    )
    db.add(response)
    db.flush()

    evaluation = judge_response(
        db, response, provider="openai", model_id="gpt-6-luna", question_text=question.text
    )
    db.commit()

    assert evaluation.blinded is True
    # Judging a synthetic stimulus yields a synthetic opinion.
    assert evaluation.is_synthetic is True
    assert evaluation.scores[0]["evidence_class"] == "ai_judge_opinion"
    # The judge was not told which model wrote the text.
    assert "claude-sonnet-5-5" not in judge.saw[0]
    assert "anthropic" not in judge.saw[0]

    stored = db.execute(
        select(JudgeEvaluation).where(JudgeEvaluation.response_id == response.id)
    ).scalars().all()
    assert len(stored) == 1


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def test_markdown_report_warns_about_synthetic_data(db, question, mock_provider):
    from explanationlab.experiments.orchestrator import (
        ExperimentSpec,
        ModelRef,
        create_experiment,
        execute_run,
    )
    from explanationlab.reports import exports

    experiment, _ = create_experiment(
        db,
        ExperimentSpec(
            name="Report test",
            type="baseline",
            question_ids=[question.id],
            source_models=[ModelRef("openai", "gpt-6.1-sol")],
            objective="Check report generation",
            hypothesis="It generates",
        ),
    )
    db.commit()
    run = db.execute(
        select(ExperimentRun).where(ExperimentRun.experiment_id == experiment.id)
    ).scalars().first()
    response = execute_run(db, run)
    db.commit()

    markdown = exports.experiment_markdown(db, experiment)
    assert "# Report test" in markdown
    assert "Check report generation" in markdown
    assert "## Limitations" in markdown
    assert "comprehension measures" in markdown
    assert "SYNTHETIC" not in markdown  # mock provider is not synthetic

    # Now flag the response synthetic and confirm the banner appears.
    response.is_synthetic = True
    db.commit()
    assert "SYNTHETIC DEMO DATA" in exports.experiment_markdown(db, experiment)

    csv_text = exports.experiment_csv(db, experiment)
    assert "response_id" in csv_text
    assert "CONTAINS SYNTHETIC DEMO DATA" in csv_text

    payload = exports.experiment_json(db, experiment)
    assert payload["contains_synthetic_data"] is True
    assert payload["responses"][0]["system_prompt_snapshot"]
