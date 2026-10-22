"""AI-assisted evaluation (§8.2) and AI-assisted grading.

Bias controls, each addressing a documented failure mode of LLM judges:

- **Blinding**: the judge never receives provider, model ID, condition label or
  treatment names. It sees an explanation and a learner profile.
- **Order randomisation**: in pairwise mode the two texts are shuffled under a
  recorded seed, so position bias is at least randomised rather than systematic.
- **No self-identification**: the prompt does not mention that a model wrote the
  text, to limit self-enhancement bias.
- **Separable output**: per-dimension scores with evidence and confidence; no
  composite number.

The result is stored as ``JudgeEvaluation`` and surfaced as *AI judge opinion*.
It is never promoted to comprehension evidence.
"""

from __future__ import annotations

import random

from sqlalchemy.orm import Session

from ..enums import CallPurpose
from ..gateway import call_structured
from ..models import JudgeEvaluation, Response
from ..prompts.safety import GUARD_INSTRUCTION, untrusted_block
from ..providers.base import GenerationRequest
from ..transformations.base import schema_instruction
from .rubrics import (
    GRADING_SCHEMA,
    JUDGE_DIMENSIONS,
    JUDGE_RUBRIC_KEY,
    JUDGE_RUBRIC_VERSION,
    JUDGE_SCHEMA,
    rubric_text,
)

JUDGE_SYSTEM = """\
You are evaluating how well a written explanation would transfer understanding to
a specific human reader.

What you are NOT judging:
- whether the explanation is well written, elegant, or pleasant
- whether it is long or short
- whether it looks visually appealing
- how intelligent its author seems

What you ARE judging: whether this reader could follow the statements, build a
model of the concept, understand the mechanism, and apply it to a new case.

Rules:
- Score each dimension independently. Do not let one dimension pull the others.
- Quote a verbatim span from the explanation as evidence for every score.
- Use the full range. If a dimension is genuinely a 2, score 2.
- State low confidence where the text does not give you enough to judge.
- Do not reward length. A complete short explanation beats a padded long one.
- Do not penalise necessary technical vocabulary that is defined at first use.
- You do not know who or what wrote this text. Do not speculate.

Rubric:
{rubric}
"""


def judge_response(
    db: Session,
    response: Response,
    *,
    provider: str,
    model_id: str,
    learner_description: str = "unspecified",
    question_text: str = "",
    effort: str | None = None,
    experiment_id: str | None = None,
) -> JudgeEvaluation:
    """Evaluate one explanation, blinded."""
    user = "\n\n".join(
        [
            f"The explanation is intended to answer: {question_text or '(not supplied)'}",
            f"Intended reader: {learner_description}",
            "Explanation to evaluate:",
            untrusted_block("explanation_under_evaluation", response.text),
            schema_instruction(JUDGE_SCHEMA, "judge_evaluation"),
        ]
    )
    data, outcome = call_structured(
        db,
        provider=provider,
        model_id=model_id,
        request=GenerationRequest(
            system=JUDGE_SYSTEM.format(rubric=rubric_text()) + "\n\n" + GUARD_INSTRUCTION,
            user=user,
            max_output_tokens=5000,
            effort=effort,
            json_schema=JUDGE_SCHEMA,
            json_schema_name="judge_evaluation",
        ),
        purpose=CallPurpose.JUDGE,
        experiment_id=experiment_id,
    )

    scores = _normalise_scores(data.get("scores") or [])
    evaluation = JudgeEvaluation(
        response_id=response.id,
        provider=provider,
        model_id=model_id,
        rubric_key=JUDGE_RUBRIC_KEY,
        rubric_version=JUDGE_RUBRIC_VERSION,
        blinded=True,
        presentation_order=[response.id],
        scores=scores,
        overall_notes=data.get("overall_notes", ""),
        input_tokens=outcome.result.input_tokens,
        output_tokens=outcome.result.output_tokens,
        cost_usd=outcome.cost_usd,
        # A judge opinion about synthetic text is itself synthetic.
        is_synthetic=outcome.result.is_synthetic or response.is_synthetic,
    )
    db.add(evaluation)
    db.flush()
    return evaluation


def _normalise_scores(raw: list) -> list[dict]:
    """Keep only known dimensions, clamp to the scale, preserve evidence."""
    known = {d["metric"] for d in JUDGE_DIMENSIONS}
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        metric = item.get("metric")
        if metric not in known:
            continue
        try:
            score = int(round(float(item.get("score"))))
        except (TypeError, ValueError):
            continue
        out.append(
            {
                "metric": metric,
                "score": max(1, min(5, score)),
                "rationale": str(item.get("rationale", ""))[:2000],
                "evidence": str(item.get("evidence", ""))[:2000],
                "confidence": item.get("confidence") or "medium",
                "improvement_suggestion": str(item.get("improvement_suggestion", ""))[:1000],
                "evidence_class": "ai_judge_opinion",
            }
        )
    return out


def blinded_pair_order(response_ids: list[str], seed: int) -> list[str]:
    """Shuffle presentation order reproducibly, to randomise position bias."""
    rng = random.Random(seed)
    ordered = list(response_ids)
    rng.shuffle(ordered)
    return ordered


# ---------------------------------------------------------------------------
# AI-assisted grading of free-text answers
# ---------------------------------------------------------------------------

GRADING_SYSTEM = """\
You are grading a learner's free-text answer against a rubric.

- Grade only what the learner wrote. Do not credit knowledge they did not show.
- Accept correct answers phrased differently from the rubric's wording. You are
  grading understanding, not vocabulary.
- Do not reward length or confidence.
- Separately report whether the answer reveals a specific incorrect
  understanding, and say what it is. A blank or vague answer is not a
  misconception; a confidently wrong causal model is.

Your score is a SUGGESTION for a human grader. It does not stand alone.
"""


def grade_short_answer(
    db: Session,
    *,
    provider: str,
    model_id: str,
    question_prompt: str,
    learner_answer: str,
    rubric: dict,
    reference_claims: list[str] | None = None,
    effort: str | None = None,
) -> tuple[dict, float]:
    """Return (grade payload, cost). The caller stores it as a *suggestion*."""
    criteria_lines = [
        f"{c.get('score')}: {c.get('label')} — {c.get('descriptor')}"
        for c in (rubric.get("criteria") or [])
    ]
    user = "\n\n".join(
        [
            f"Assessment question:\n{question_prompt}",
            "Rubric (score: label — descriptor):\n" + "\n".join(criteria_lines),
            f"Maximum score: {rubric.get('max_score', 1.0)}",
            (
                "Claims a correct answer would reflect:\n"
                + "\n".join(f"- {c}" for c in reference_claims)
                if reference_claims
                else ""
            ),
            "Learner's answer:",
            untrusted_block("learner_answer", learner_answer),
            schema_instruction(GRADING_SCHEMA, "short_answer_grade"),
        ]
    )
    data, outcome = call_structured(
        db,
        provider=provider,
        model_id=model_id,
        request=GenerationRequest(
            system=GRADING_SYSTEM + "\n\n" + GUARD_INSTRUCTION,
            user=user,
            max_output_tokens=1500,
            effort=effort,
            json_schema=GRADING_SCHEMA,
            json_schema_name="short_answer_grade",
        ),
        purpose=CallPurpose.GRADING,
    )

    max_score = float(rubric.get("max_score", 1.0))
    try:
        score = max(0.0, min(max_score, float(data.get("score", 0))))
    except (TypeError, ValueError):
        score = 0.0

    return (
        {
            "score": score,
            "rationale": str(data.get("rationale", ""))[:2000],
            "misconception_detected": bool(data.get("misconception_detected")),
            "misconception_detail": str(data.get("misconception_detail", ""))[:1000],
            "is_synthetic": outcome.result.is_synthetic,
            "grader": f"{provider}:{model_id}",
            "status": "ai_suggestion_pending_human_review",
        },
        outcome.cost_usd,
    )
