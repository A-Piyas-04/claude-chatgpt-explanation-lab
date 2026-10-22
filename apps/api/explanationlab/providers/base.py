"""Provider-agnostic generation contract.

Every model call in the platform — baseline generation, transformation stages,
judging, concept extraction, AI-assisted grading — goes through this interface.
That is what makes the transformation engine portable to a Claude Skill or a
standalone service later (Principle 6 and 8).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from ..enums import Provider


class ProviderError(RuntimeError):
    """A real provider failure. Surfaced to the researcher, never swallowed."""

    def __init__(self, message: str, *, error_type: str = "provider_error", status: int | None = None):
        super().__init__(message)
        self.error_type = error_type
        self.status = status


class ProviderNotConfigured(ProviderError):
    def __init__(self, provider: str):
        super().__init__(
            f"Provider '{provider}' has no API key configured. "
            "Set it in .env, or run in demo mode.",
            error_type="provider_not_configured",
        )


@dataclass(slots=True)
class ModelCapabilities:
    """What a specific model actually accepts.

    Current frontier models *reject* parameters older ones accepted, so this is
    load-bearing rather than cosmetic.
    """

    supports_temperature: bool = False
    supports_effort: bool = True
    supports_max_output_tokens: bool = True
    supports_structured_output: bool = True
    default_effort: str | None = None


@dataclass(slots=True)
class GenerationRequest:
    system: str
    user: str
    max_output_tokens: int = 4096
    temperature: float | None = None
    effort: str | None = None
    # When set, the provider is asked to return JSON matching this schema.
    json_schema: dict | None = None
    json_schema_name: str = "structured_output"

    def cache_key(self, provider: str, model_id: str) -> str:
        """Stable hash of everything that can change the output.

        Requests carrying a temperature are still hashed with it, but callers
        decide whether a request is cacheable at all (see ``is_deterministic``).
        """
        payload = {
            "provider": provider,
            "model": model_id,
            "system": self.system,
            "user": self.user,
            "max_output_tokens": self.max_output_tokens,
            "temperature": self.temperature,
            "effort": self.effort,
            "json_schema": self.json_schema,
        }
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    @property
    def is_deterministic(self) -> bool:
        """Only temperature-0 (or temperature-less) requests are cache-safe.

        Note this is *best effort*: no current provider guarantees bitwise
        determinism. Caching is a cost control, not a reproducibility claim —
        which is why replicates are stored separately and never deduplicated.
        """
        return self.temperature in (None, 0, 0.0)


@dataclass(slots=True)
class GenerationResult:
    text: str
    provider: str
    model_id: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    finish_reason: str | None = None
    # Human-readable notes about controls the researcher asked for that this
    # model could not honour. Carried into the response row and every report.
    control_limitations: list[str] = field(default_factory=list)
    effective_settings: dict = field(default_factory=dict)
    served_from_cache: bool = False
    is_synthetic: bool = False
    raw_json: dict | None = None


class BaseProvider:
    """Adapter interface."""

    name: Provider

    def capabilities(self, model_id: str) -> ModelCapabilities:  # pragma: no cover - abstract
        raise NotImplementedError

    def generate(self, model_id: str, request: GenerationRequest) -> GenerationResult:
        raise NotImplementedError  # pragma: no cover - abstract

    def list_models(self) -> list[str]:
        """Live model IDs from the provider, when the API exposes them."""
        return []

    # -- shared helpers ----------------------------------------------------

    @staticmethod
    def reconcile_settings(
        request: GenerationRequest, caps: ModelCapabilities
    ) -> tuple[dict, list[str]]:
        """Drop unsupported parameters and say so, instead of pretending.

        Returns the settings that will actually be sent plus a list of
        limitation notes recorded against the run.
        """
        effective: dict = {}
        limitations: list[str] = []

        if caps.supports_max_output_tokens:
            effective["max_output_tokens"] = request.max_output_tokens
        elif request.max_output_tokens:
            limitations.append("max_output_tokens not supported by this model; omitted")

        if request.temperature is not None:
            if caps.supports_temperature:
                effective["temperature"] = request.temperature
            else:
                limitations.append(
                    f"temperature={request.temperature} requested but this model rejects "
                    "the temperature parameter; omitted. Generation conditions are therefore "
                    "NOT identical to a temperature-controlled model."
                )

        if request.effort is not None:
            if caps.supports_effort:
                effective["effort"] = request.effort
            else:
                limitations.append(
                    f"effort={request.effort} requested but this model has no effort control; omitted"
                )
        elif caps.supports_effort and caps.default_effort:
            effective["effort"] = caps.default_effort
            limitations.append(
                f"no effort specified; provider default '{caps.default_effort}' applies"
            )

        if request.json_schema is not None and not caps.supports_structured_output:
            limitations.append(
                "structured output not supported by this model; schema supplied in the "
                "prompt and the response parsed defensively"
            )

        return effective, limitations
