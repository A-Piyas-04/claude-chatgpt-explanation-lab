"""Offline demo provider.

Purpose: the app must stay fully navigable with **no API keys and no spend**, so
a reviewer can see every screen and every workflow end to end.

Hard rules enforced here and downstream:

- Every result carries ``is_synthetic=True``. That flag is copied onto the
  response row, every derived transformation, every evaluation, every usage
  record, and every aggregate. It is rendered as a warning wherever it appears.
- Output is deterministic (seeded by a hash of the request) so demo runs and
  tests are reproducible.
- Nothing here may be presented as a research finding.
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from pathlib import Path

from ..enums import Provider
from .base import BaseProvider, GenerationRequest, GenerationResult, ModelCapabilities

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "demo_explanations.json"


def _load_fixtures() -> dict:
    if FIXTURE_PATH.exists():
        return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {"styles": {}, "fallback": {}}


class DemoProvider(BaseProvider):
    """Fixture-backed stand-in for a real provider."""

    name = Provider.MANUAL

    def __init__(self, emulating: str = "demo") -> None:
        self.emulating = emulating
        self._fixtures = _load_fixtures()

    def capabilities(self, model_id: str) -> ModelCapabilities:
        return ModelCapabilities(
            supports_temperature=True,
            supports_effort=True,
            supports_max_output_tokens=True,
            supports_structured_output=True,
            default_effort=None,
        )

    def generate(self, model_id: str, request: GenerationRequest) -> GenerationResult:
        started = time.perf_counter()
        seed_src = request.cache_key(self.emulating, model_id)
        rng = random.Random(int(seed_src[:12], 16))

        if request.json_schema is not None:
            text = json.dumps(
                self._structured_payload(request, rng), ensure_ascii=False, indent=2
            )
        else:
            text = self._explanation(request, model_id, rng)

        # Plausible but clearly fabricated token counts.
        input_tokens = max(1, len((request.system + request.user).split()))
        output_tokens = max(1, len(text.split()))
        latency_ms = int((time.perf_counter() - started) * 1000) + rng.randint(400, 1800)

        return GenerationResult(
            text=text,
            provider=self.emulating,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            finish_reason="end_turn",
            control_limitations=[
                "DEMO MODE: this output is a local fixture, not a model response. "
                "It carries no evidential value."
            ],
            effective_settings={"demo": True},
            is_synthetic=True,
        )

    # -- explanation fixtures ---------------------------------------------

    def _explanation(self, request: GenerationRequest, model_id: str, rng: random.Random) -> str:
        """Pick a style that reflects how the condition was configured.

        Demo mode is more useful if it *demonstrates the contrast the research is
        about*: a terse system prompt yields the dense style, a pedagogical one
        yields the scaffolded style. This is a scripted illustration of the
        hypothesis, never evidence for it.
        """
        system = request.system.lower()
        if any(k in system for k in ("prerequisite", "teaching process", "learner level")):
            style = "scaffolded"
        elif any(k in system for k in ("tutor", "step by step", "simple language")):
            style = "tutor"
        else:
            style = "dense"

        styles = self._fixtures.get("styles", {})
        template = styles.get(style) or styles.get("dense") or "{question}\n\n(demo fixture)"
        question = self._extract_question(request.user)
        topic = question.rstrip("?").strip() or "the topic"
        return template.replace("{question}", question).replace("{topic}", topic)

    @staticmethod
    def _extract_question(user_text: str) -> str:
        for line in user_text.splitlines():
            stripped = line.strip()
            if stripped.endswith("?"):
                return stripped
        return user_text.strip()[:300]

    # -- structured payloads ----------------------------------------------

    def _structured_payload(self, request: GenerationRequest, rng: random.Random) -> dict:
        handler = {
            "input_analysis": self._demo_analysis,
            "pedagogical_plan": self._demo_plan,
            "fidelity_check": self._demo_fidelity,
            "judge_evaluation": self._demo_judge,
            "concept_graph": self._demo_concept_graph,
            "short_answer_grade": self._demo_grade,
        }.get(request.json_schema_name)
        if handler:
            return handler(request, rng)
        return self._synthesize(request.json_schema or {}, rng)

    def _demo_analysis(self, request: GenerationRequest, rng: random.Random) -> dict:
        return {
            "main_topic": "[demo] " + self._extract_question(request.user)[:120],
            "primary_claims": [
                "[demo] The system stores recently used results in fast memory.",
                "[demo] Repeat requests are served without touching the slower store.",
            ],
            "key_concepts": ["cache", "latency", "hit rate", "eviction"],
            "prerequisite_concepts": ["memory hierarchy", "client-server request flow"],
            "technical_vocabulary": [
                {"term": "eviction policy", "explained_in_text": False},
                {"term": "hit rate", "explained_in_text": True},
            ],
            "existing_examples": ["[demo] a product page being requested twice"],
            "missing_intermediate_steps": [
                "[demo] does not say what happens on a cache miss before the store responds"
            ],
            "assumed_prior_knowledge": ["what a database query costs"],
            "possible_confusions": ["[demo] 'invalidation' is used before it is defined"],
            "ambiguous_references": ["[demo] 'it' in paragraph 3 could be the cache or the store"],
        }

    def _demo_plan(self, request: GenerationRequest, rng: random.Random) -> dict:
        return {
            "learner_level": "intermediate",
            "learning_objectives": [
                "[demo] explain why repeated reads are cheap",
                "[demo] predict behaviour on a cache miss",
            ],
            "prerequisite_order": ["request flow", "cost of a query", "cache", "invalidation"],
            "explanation_sequence": [
                "motivate with a slow page",
                "introduce the cache",
                "trace a hit then a miss",
                "cover staleness",
            ],
            "needs_concrete_example": True,
            "needs_analogy": True,
            "needs_diagram": True,
            "analogy_rationale": "[demo] a lookup table is familiar and maps cleanly",
            "detail_level": "moderate",
            "techniques_not_needed": ["T4 analogy would be redundant for an advanced profile"],
        }

    def _demo_fidelity(self, request: GenerationRequest, rng: random.Random) -> dict:
        return {
            "verdict": "warnings",
            "warnings": [
                {
                    "type": "new_claim",
                    "severity": "medium",
                    "detail": "[demo] transformed text asserts a 10x speedup absent from the source",
                    "source_excerpt": "",
                    "transformed_excerpt": "[demo] 'roughly ten times faster'",
                },
                {
                    "type": "omitted_caveat",
                    "severity": "low",
                    "detail": "[demo] the source's note about stale reads is not carried over",
                    "source_excerpt": "[demo] 'data can be briefly out of date'",
                    "transformed_excerpt": "",
                },
            ],
            "numeric_drift": [],
            "preserved_claims": ["[demo] repeat requests avoid the database"],
            "notes": "DEMO fixture. Not a factual verification.",
        }

    def _demo_judge(self, request: GenerationRequest, rng: random.Random) -> dict:
        dims = [
            "clarity",
            "logical_progression",
            "prerequisite_handling",
            "mechanism_explanation",
            "example_quality",
            "audience_suitability",
            "unnecessary_complexity",
            "information_loss",
            "factual_fidelity",
        ]
        return {
            "scores": [
                {
                    "metric": d,
                    "score": rng.choice([2, 3, 3, 4, 4, 5]),
                    "rationale": f"[demo] scripted rationale for {d}",
                    "evidence": "[demo] quoted span would appear here",
                    "confidence": rng.choice(["low", "medium", "high"]),
                    "improvement_suggestion": f"[demo] suggestion for {d}",
                }
                for d in dims
            ],
            "overall_notes": "DEMO fixture. A judge model's opinion is not comprehension evidence.",
        }

    def _demo_concept_graph(self, request: GenerationRequest, rng: random.Random) -> dict:
        nodes = [
            {"id": "request_flow", "label": "Request flow", "importance": "core"},
            {"id": "query_cost", "label": "Cost of a database query", "importance": "core"},
            {"id": "cache", "label": "Cache", "importance": "core"},
            {"id": "hit_miss", "label": "Hit and miss", "importance": "core"},
            {"id": "invalidation", "label": "Invalidation", "importance": "supporting"},
            {"id": "eviction", "label": "Eviction policy", "importance": "optional"},
        ]
        edges = [
            {"source": "request_flow", "target": "cache", "relation": "prerequisite_for"},
            {"source": "query_cost", "target": "cache", "relation": "motivates"},
            {"source": "cache", "target": "hit_miss", "relation": "prerequisite_for"},
            {"source": "hit_miss", "target": "invalidation", "relation": "prerequisite_for"},
            {"source": "cache", "target": "eviction", "relation": "prerequisite_for"},
        ]
        return {
            "nodes": nodes,
            "edges": edges,
            "notes": "DEMO fixture. Inferred prerequisite edges are hypotheses.",
        }

    def _demo_grade(self, request: GenerationRequest, rng: random.Random) -> dict:
        return {
            "score": rng.choice([0.0, 0.5, 1.0]),
            "rationale": "[demo] scripted grading rationale; requires human review",
            "misconception_detected": rng.choice([True, False]),
            "misconception_detail": "[demo] learner may think the cache is the source of truth",
        }

    # -- generic JSON-schema synthesiser ----------------------------------

    def _synthesize(self, schema: dict, rng: random.Random, depth: int = 0):
        if depth > 6:
            return None
        stype = schema.get("type")
        if "enum" in schema:
            return schema["enum"][0]
        if stype == "object":
            props = schema.get("properties", {})
            return {k: self._synthesize(v, rng, depth + 1) for k, v in props.items()}
        if stype == "array":
            item = schema.get("items", {"type": "string"})
            return [self._synthesize(item, rng, depth + 1)]
        if stype == "integer":
            return rng.randint(1, 5)
        if stype == "number":
            return round(rng.uniform(0, 5), 2)
        if stype == "boolean":
            return rng.choice([True, False])
        return "[demo synthetic value]"
