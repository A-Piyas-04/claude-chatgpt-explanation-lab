"""Stage D — fidelity verification.

Two independent layers, because an LLM judging its own family's rewrite is a
weak check on its own:

1. **Deterministic checks** (this module, no model call): numeric drift, hedge
   removal, and treatment-boundary violations. Cheap, reproducible, and
   auditable — a researcher can verify them by hand.
2. **An LLM reviewer** that reads source and transformed text side by side.

Neither proves correctness. The verdict is always labelled provisional, and
"clean" means "no problems were detected", never "verified accurate".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Numbers with optional unit/suffix. Deliberately broad: a false positive costs
# a researcher ten seconds, a false negative corrupts a stimulus.
_NUMBER_RE = re.compile(
    r"(?<![\w.])(\d+(?:[.,]\d+)?)\s*(%|ms|s|m|h|kb|mb|gb|tb|bits?|bytes?|x|×|k|bn|million|billion)?",
    re.IGNORECASE,
)

_HEDGES = (
    "may ",
    "might ",
    "can ",
    "often",
    "sometimes",
    "usually",
    "typically",
    "approximately",
    "roughly",
    "about ",
    "in most cases",
    "generally",
    "tends to",
    "not always",
    "assuming",
    "provided that",
    "unless",
    "caveat",
    "limitation",
    "however",
    "but only if",
)

_CERTAINTY_MARKERS = (
    "always",
    "never",
    "guarantees",
    "guaranteed",
    "certainly",
    "definitely",
    "must always",
    "in all cases",
    "proves",
    "impossible",
)


@dataclass(slots=True)
class DeterministicFindings:
    numeric_drift: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"numeric_drift": self.numeric_drift, "warnings": self.warnings}


def _numbers(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value, unit in _NUMBER_RE.findall(text):
        normalised = value.replace(",", ".")
        key = f"{normalised}{(unit or '').lower()}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def check_numeric_drift(source: str, transformed: str) -> list[dict]:
    """Numbers that vanished or appeared. A changed figure is a hard failure."""
    src = _numbers(source)
    dst = _numbers(transformed)
    drift: list[dict] = []

    for key, count in src.items():
        if dst.get(key, 0) < count:
            drift.append(
                {
                    "source_value": key,
                    "transformed_value": "(absent or fewer occurrences)",
                    "context": "present in the source, missing from the transformed text",
                    "direction": "removed",
                }
            )
    for key, count in dst.items():
        if src.get(key, 0) < count:
            drift.append(
                {
                    "source_value": "(not present)",
                    "transformed_value": key,
                    "context": "appears in the transformed text but not in the source",
                    "direction": "added",
                }
            )
    return drift


def check_hedge_loss(source: str, transformed: str) -> list[dict]:
    """Hedges removed or absolutes introduced — the quiet way certainty creeps in."""
    src_l, dst_l = source.lower(), transformed.lower()
    warnings: list[dict] = []

    lost = [h for h in _HEDGES if src_l.count(h) > dst_l.count(h)]
    if lost:
        warnings.append(
            {
                "type": "omitted_caveat",
                "severity": "medium",
                "detail": (
                    "Hedging language occurs less often after transformation: "
                    + ", ".join(sorted({h.strip() for h in lost})[:8])
                    + ". Check that no condition or limitation was dropped."
                ),
                "source_excerpt": "",
                "transformed_excerpt": "",
                "detector": "deterministic",
            }
        )

    gained = [c for c in _CERTAINTY_MARKERS if dst_l.count(c) > src_l.count(c)]
    if gained:
        warnings.append(
            {
                "type": "unjustified_certainty",
                "severity": "medium",
                "detail": (
                    "Absolute language appears more often after transformation: "
                    + ", ".join(sorted(set(gained))[:8])
                    + ". Check the source supports the stronger claim."
                ),
                "source_excerpt": "",
                "transformed_excerpt": "",
                "detector": "deterministic",
            }
        )
    return warnings


def check_information_loss(source: str, transformed: str, *, threshold: float = 0.55) -> list[dict]:
    """Flag a large drop in length.

    Length is a crude proxy, but a transformation that halves the text has
    almost certainly dropped content, and Cognitive Load Theory is explicit that
    removing intrinsic content is not a reduction in load (see
    Docs/RESEARCH_FOUNDATIONS.md §2).
    """
    src_words = len(source.split())
    dst_words = len(transformed.split())
    if src_words < 80 or dst_words == 0:
        return []
    ratio = dst_words / src_words
    if ratio < threshold:
        return [
            {
                "type": "information_loss",
                "severity": "high" if ratio < 0.4 else "medium",
                "detail": (
                    f"Transformed text is {ratio:.0%} the length of the source "
                    f"({src_words} -> {dst_words} words). Verify that content was "
                    "reworded rather than dropped."
                ),
                "source_excerpt": "",
                "transformed_excerpt": "",
                "detector": "deterministic",
            }
        ]
    return []


_HEADING_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)
_LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s", re.MULTILINE)
_TABLE_RE = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)


def check_boundary_violations(
    treatment_key: str, source: str, transformed: str
) -> list[dict]:
    """Did a treatment do another treatment's job?

    Without this, an ablation design silently collapses: a "vocabulary only"
    variant that also added headings and an analogy is not a vocabulary variant.
    """
    warnings: list[dict] = []

    def added(pattern: re.Pattern) -> int:
        return max(0, len(pattern.findall(transformed)) - len(pattern.findall(source)))

    structural_added = added(_HEADING_RE) + added(_TABLE_RE)
    lists_added = added(_LIST_RE)

    # T1, T2, T3, T4 and T6 are all forbidden from adding presentation structure.
    if treatment_key in {"T1", "T2", "T3", "T4", "T6"} and (structural_added > 0 or lists_added > 2):
        warnings.append(
            {
                "type": "boundary_violation",
                "severity": "medium",
                "detail": (
                    f"Treatment {treatment_key} added presentation structure "
                    f"({structural_added} headings/tables, {lists_added} list items). "
                    "That is T5's role. This variant is not a clean single-treatment "
                    "condition and should be excluded from strict ablation analysis."
                ),
                "detector": "deterministic",
            }
        )

    # T5 is presentation-only: the prose should be near-identical.
    if treatment_key == "T5":
        src_words = len(re.sub(r"[^\w\s]", " ", source).split())
        dst_words = len(re.sub(r"[^\w\s]", " ", transformed).split())
        if src_words and abs(dst_words - src_words) / src_words > 0.35:
            warnings.append(
                {
                    "type": "boundary_violation",
                    "severity": "medium",
                    "detail": (
                        f"Treatment T5 changed word count by "
                        f"{abs(dst_words - src_words) / src_words:.0%} "
                        f"({src_words} -> {dst_words}). T5 is presentation-only, so a large "
                        "change suggests the prose was rewritten as well."
                    ),
                    "detector": "deterministic",
                }
            )
    return warnings


def run_deterministic_checks(
    source: str, transformed: str, treatments: list[str]
) -> DeterministicFindings:
    findings = DeterministicFindings()
    findings.numeric_drift = check_numeric_drift(source, transformed)
    if findings.numeric_drift:
        findings.warnings.append(
            {
                "type": "numeric_change",
                "severity": "high",
                "detail": (
                    f"{len(findings.numeric_drift)} numeric difference(s) detected between "
                    "source and transformed text. Numbers must not change."
                ),
                "detector": "deterministic",
            }
        )
    findings.warnings.extend(check_hedge_loss(source, transformed))
    findings.warnings.extend(check_information_loss(source, transformed))
    for key in treatments:
        findings.warnings.extend(check_boundary_violations(key, source, transformed))
    return findings


# ---------------------------------------------------------------------------
# LLM reviewer prompt
# ---------------------------------------------------------------------------

FIDELITY_SYSTEM = """\
You are auditing whether a rewritten technical explanation still says the same
thing as the original. You are not judging which version reads better, and you
are not fact-checking either version against the world — only against each other.

Report a warning for each of these you find:
- altered_claim: a technical assertion whose meaning changed
- new_claim: an assertion in the rewrite that the source does not support
- omitted_claim: a substantive assertion dropped
- omitted_caveat: a limitation, condition or exception dropped
- numeric_change: any changed number, unit, or quantity
- contradiction: the two versions disagree
- misleading_analogy: an added comparison that implies something false
- false_simplification: a simplification that is now wrong rather than merely less precise
- unjustified_certainty: hedged in the source, asserted in the rewrite
- information_loss: substantive content removed rather than reworded

Rewording, reordering, reformatting and added structure are NOT warnings on their
own. Only report a difference in what the text claims.

Be specific: quote the relevant span from each version. If you find nothing,
return an empty warnings list and verdict "clean" — which means only that you
detected no problems, not that the rewrite is verified correct.\
"""


def build_fidelity_user_prompt(
    source: str, transformed: str, factual_checklist: list[str] | None = None
) -> str:
    from ..prompts.safety import untrusted_block

    parts = [
        "ORIGINAL EXPLANATION:",
        untrusted_block("original_explanation", source),
        "",
        "REWRITTEN EXPLANATION:",
        untrusted_block("rewritten_explanation", transformed),
    ]
    if factual_checklist:
        parts += [
            "",
            "The reviewed factual checklist for this question lists the claims a correct "
            "explanation should contain. For each, say whether the rewritten text still "
            "contains it:",
            *[f"- {claim}" for claim in factual_checklist],
        ]
    return "\n".join(parts)
