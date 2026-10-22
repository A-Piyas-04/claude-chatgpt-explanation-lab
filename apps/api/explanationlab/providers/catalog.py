"""Seed model catalogue with capability and pricing records.

Verified against official provider documentation on **2026-10-22**:

- OpenAI pricing/models: https://developers.openai.com/api/docs/pricing
- Anthropic pricing/models: https://docs.anthropic.com/en/docs/about-claude/models

Two deliberate design choices:

1. **Nothing here is hardcoded into the experiment logic.** This is a seed for a
   database table the researcher can edit, and ``POST /api/models/refresh``
   reconciles it against each provider's live model list. Model IDs go stale;
   treating this file as authoritative forever is how a research tool ends up
   silently calling a retired model.
2. **Prices are an operator-configurable estimate.** Cost figures in the UI are
   labelled estimates, because real billing depends on tier, caching and
   discounts we cannot see from here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ..enums import Provider

PRICING_VERIFIED_ON = "2026-10-22"


@dataclass(slots=True)
class CatalogSeed:
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
    notes: str

    def as_row(self) -> dict:
        data = asdict(self)
        data["pricing_source"] = f"provider documentation, verified {PRICING_VERIFIED_ON}"
        return data


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------
# Capability notes that matter for experimental control:
#   * `temperature` is REJECTED with HTTP 400 on the current generation
#     (Opus 5.5 / Sonnet 5.5 / Haiku 5.5) — it is not merely ignored.
#   * Thinking cannot be disabled on Opus 5.5; depth is set via
#     `output_config.effort`, whose default on that model is `medium`.
#   * Structured extraction uses `output_config.format` with a JSON schema,
#     because forced tool use returns 400 on these models.

ANTHROPIC_SEEDS = [
    CatalogSeed(
        provider=Provider.ANTHROPIC.value,
        model_id="claude-opus-5-5",
        display_name="Claude Opus 5.5",
        tier="frontier",
        input_cost_per_mtok=4.00,
        output_cost_per_mtok=20.00,
        context_window=1_000_000,
        supports_temperature=False,
        supports_effort=True,
        supports_max_output_tokens=True,
        supports_structured_output=True,
        default_effort="medium",
        notes=(
            "Rejects temperature (HTTP 400). Thinking cannot be disabled; use effort. "
            "Provider default effort is medium."
        ),
    ),
    CatalogSeed(
        provider=Provider.ANTHROPIC.value,
        model_id="claude-sonnet-5-5",
        display_name="Claude Sonnet 5.5",
        tier="balanced",
        input_cost_per_mtok=2.00,
        output_cost_per_mtok=10.00,
        context_window=1_000_000,
        supports_temperature=False,
        supports_effort=True,
        supports_max_output_tokens=True,
        supports_structured_output=True,
        default_effort="high",
        notes="Rejects non-default temperature (HTTP 400). Effort default is high.",
    ),
    CatalogSeed(
        provider=Provider.ANTHROPIC.value,
        model_id="claude-haiku-5-5",
        display_name="Claude Haiku 5.5",
        tier="economy",
        input_cost_per_mtok=0.10,
        output_cost_per_mtok=0.50,
        context_window=1_000_000,
        supports_temperature=False,
        supports_effort=True,
        supports_max_output_tokens=True,
        supports_structured_output=True,
        default_effort="medium",
        notes=(
            "Rejects non-default temperature. Listed prices apply up to 100K input tokens; "
            "longer prompts are billed higher."
        ),
    ),
]

# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------
# Current models are served through the Responses API. Structured outputs nest
# as text.format.{type,name,strict,schema}.

OPENAI_SEEDS = [
    CatalogSeed(
        provider=Provider.OPENAI.value,
        model_id="gpt-6-astra",
        display_name="GPT-6 Astra",
        tier="frontier",
        input_cost_per_mtok=10.00,
        output_cost_per_mtok=50.00,
        context_window=272_000,
        supports_temperature=False,
        supports_effort=True,
        supports_max_output_tokens=True,
        supports_structured_output=True,
        default_effort=None,
        notes=(
            "Flagship. Reasoning model: sampling controls are not accepted. "
            "Standard-tier short-context pricing."
        ),
    ),
    CatalogSeed(
        provider=Provider.OPENAI.value,
        model_id="gpt-6.1-sol",
        display_name="GPT-6.1 Sol",
        tier="balanced",
        input_cost_per_mtok=2.00,
        output_cost_per_mtok=10.00,
        context_window=272_000,
        supports_temperature=False,
        supports_effort=True,
        supports_max_output_tokens=True,
        supports_structured_output=True,
        default_effort=None,
        notes="Mid-tier; balances intelligence and cost.",
    ),
    CatalogSeed(
        provider=Provider.OPENAI.value,
        model_id="gpt-6-luna",
        display_name="GPT-6 Luna",
        tier="economy",
        input_cost_per_mtok=0.10,
        output_cost_per_mtok=0.50,
        context_window=272_000,
        supports_temperature=False,
        supports_effort=True,
        supports_max_output_tokens=True,
        supports_structured_output=True,
        default_effort=None,
        notes="Small model for cost-sensitive, high-volume work (e.g. bulk judging).",
    ),
    CatalogSeed(
        provider=Provider.OPENAI.value,
        model_id="gpt-5.4",
        display_name="GPT-5.4 (previous generation)",
        tier="legacy",
        input_cost_per_mtok=2.50,
        output_cost_per_mtok=15.00,
        context_window=400_000,
        supports_temperature=True,
        supports_effort=False,
        supports_max_output_tokens=True,
        supports_structured_output=True,
        default_effort=None,
        notes=(
            "Kept deliberately: it still accepts `temperature`, which makes it the only "
            "way to run a temperature-controlled condition. Useful for separating "
            "sampling effects from model effects."
        ),
    ),
]

ALL_SEEDS = ANTHROPIC_SEEDS + OPENAI_SEEDS

# Fallback capabilities for a model ID discovered live but absent from the seed
# list. Conservative: assume no sampling control, so we never send a parameter
# that 400s, and flag the uncertainty.
UNKNOWN_MODEL_NOTE = (
    "Discovered from the provider's live model list; capabilities and pricing unverified. "
    "Cost estimates are unavailable for this model."
)


def seed_rows() -> list[dict]:
    return [s.as_row() for s in ALL_SEEDS]


def find_seed(provider: str, model_id: str) -> CatalogSeed | None:
    for s in ALL_SEEDS:
        if s.provider == provider and s.model_id == model_id:
            return s
    return None


def estimate_cost_usd(
    input_tokens: int | None,
    output_tokens: int | None,
    input_cost_per_mtok: float | None,
    output_cost_per_mtok: float | None,
) -> float:
    """Estimated spend for one call. Returns 0.0 when pricing is unknown."""
    if not input_cost_per_mtok and not output_cost_per_mtok:
        return 0.0
    cost = 0.0
    if input_tokens and input_cost_per_mtok:
        cost += (input_tokens / 1_000_000) * input_cost_per_mtok
    if output_tokens and output_cost_per_mtok:
        cost += (output_tokens / 1_000_000) * output_cost_per_mtok
    return round(cost, 6)
