"""Descriptive statistics with honest uncertainty.

Implemented with the standard library only: a bootstrap needs no scipy, and
adding a dependency to compute a mean is how research tools acquire a numerical
stack nobody audits.

Two things this module refuses to do:

- Produce a p-value. With the sample sizes a solo researcher will realistically
  gather, a significance test would invite exactly the overclaiming the brief
  warns against. Intervals communicate precision without implying a decision.
- Treat correlated observations as independent. Multiple ratings of the same
  response, or multiple answers from one participant, are clustered.
  :func:`independence_warnings` detects this and the warning travels with the
  numbers into every report.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


@dataclass(slots=True)
class Summary:
    n: int
    mean: float | None = None
    sd: float | None = None
    median: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    ci_method: str | None = None
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "n": self.n,
            "mean": self.mean,
            "sd": self.sd,
            "median": self.median,
            "min": self.minimum,
            "max": self.maximum,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "ci_method": self.ci_method,
            "warnings": self.warnings,
        }


# Below this many observations we report the numbers but refuse to attach an
# interval, because a bootstrap from 4 points produces a confident-looking range
# that means nothing.
MIN_N_FOR_INTERVAL = 8
EXPLORATORY_N_THRESHOLD = 20


def summarise(
    values: list[float],
    *,
    confidence: float = 0.95,
    seed: int = 20261022,
    iterations: int = 5000,
) -> Summary:
    clean = [float(v) for v in values if v is not None]
    n = len(clean)
    if n == 0:
        return Summary(n=0, warnings=["No observations."])

    mean = sum(clean) / n
    median = _median(clean)
    sd = (
        math.sqrt(sum((v - mean) ** 2 for v in clean) / (n - 1)) if n > 1 else None
    )

    summary = Summary(
        n=n,
        mean=round(mean, 4),
        sd=round(sd, 4) if sd is not None else None,
        median=round(median, 4),
        minimum=round(min(clean), 4),
        maximum=round(max(clean), 4),
    )

    if n < MIN_N_FOR_INTERVAL:
        summary.warnings.append(
            f"n={n} is too small for a meaningful interval; none computed. "
            "Descriptive only."
        )
        return summary

    low, high = bootstrap_ci(clean, confidence=confidence, seed=seed, iterations=iterations)
    summary.ci_low = round(low, 4)
    summary.ci_high = round(high, 4)
    summary.ci_method = f"percentile bootstrap, {iterations} resamples, seed={seed}"

    if n < EXPLORATORY_N_THRESHOLD:
        summary.warnings.append(
            f"n={n}: exploratory. The interval is wide and unstable; do not treat "
            "a difference as established."
        )
    return summary


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def bootstrap_ci(
    values: list[float],
    *,
    confidence: float = 0.95,
    seed: int = 20261022,
    iterations: int = 5000,
) -> tuple[float, float]:
    """Percentile bootstrap interval for the mean. Seeded for reproducibility."""
    rng = random.Random(seed)
    n = len(values)
    means: list[float] = []
    for _ in range(iterations):
        resample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(resample) / n)
    means.sort()
    alpha = (1 - confidence) / 2
    lo_idx = max(0, int(alpha * iterations) - 1)
    hi_idx = min(iterations - 1, int((1 - alpha) * iterations))
    return means[lo_idx], means[hi_idx]


def paired_difference(
    pairs: list[tuple[float, float]],
    *,
    confidence: float = 0.95,
    seed: int = 20261022,
    iterations: int = 5000,
) -> dict:
    """Bootstrap interval on the mean within-pair difference (b - a).

    Use when the design genuinely pairs observations — the same question under
    two conditions, or the same participant before and after. Pairing is what
    makes a small-sample comparison informative at all.
    """
    clean = [(float(a), float(b)) for a, b in pairs if a is not None and b is not None]
    if not clean:
        return {"n_pairs": 0, "warnings": ["No complete pairs."]}

    diffs = [b - a for a, b in clean]
    summary = summarise(diffs, confidence=confidence, seed=seed, iterations=iterations)
    result = summary.as_dict()
    result["n_pairs"] = len(clean)
    result["mean_difference"] = result.pop("mean")
    result["interpretation"] = (
        "Interval on the mean within-pair difference. An interval spanning zero means "
        "the data do not resolve the direction of the effect."
    )
    if summary.ci_low is not None and summary.ci_high is not None:
        result["excludes_zero"] = not (summary.ci_low <= 0 <= summary.ci_high)
    return result


def cohens_d(group_a: list[float], group_b: list[float]) -> dict:
    """Standardised mean difference with a pooled SD. Descriptive only."""
    a = [float(v) for v in group_a if v is not None]
    b = [float(v) for v in group_b if v is not None]
    if len(a) < 2 or len(b) < 2:
        return {"d": None, "warnings": ["Need at least 2 observations per group."]}

    mean_a, mean_b = sum(a) / len(a), sum(b) / len(b)
    var_a = sum((v - mean_a) ** 2 for v in a) / (len(a) - 1)
    var_b = sum((v - mean_b) ** 2 for v in b) / (len(b) - 1)
    pooled = math.sqrt(
        ((len(a) - 1) * var_a + (len(b) - 1) * var_b) / (len(a) + len(b) - 2)
    )
    if pooled == 0:
        return {"d": None, "warnings": ["Zero pooled variance."]}

    return {
        "d": round((mean_b - mean_a) / pooled, 4),
        "n_a": len(a),
        "n_b": len(b),
        "note": "Effect size only. Not a test, and not evidence of a reliable difference.",
    }


def independence_warnings(
    *,
    observation_count: int,
    distinct_participants: int | None = None,
    distinct_questions: int | None = None,
    distinct_responses: int | None = None,
) -> list[str]:
    """Flag clustering that makes an n look larger than it is.

    §7: "Avoid treating individual answer ratings as independent samples if the
    same question, learner, or model response appears repeatedly."
    """
    warnings: list[str] = []
    if observation_count == 0:
        return ["No observations."]

    def check(label: str, distinct: int | None) -> None:
        if distinct is None or distinct == 0:
            return
        if distinct < observation_count:
            ratio = observation_count / distinct
            warnings.append(
                f"{observation_count} observations come from only {distinct} distinct "
                f"{label} ({ratio:.1f} per {label[:-1] if label.endswith('s') else label}). "
                "These are clustered, not independent; the effective sample size is "
                "closer to the number of distinct units."
            )

    check("participants", distinct_participants)
    check("questions", distinct_questions)
    check("model responses", distinct_responses)
    return warnings
