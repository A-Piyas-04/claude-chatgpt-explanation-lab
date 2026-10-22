"""Anthropic Messages API adapter."""

from __future__ import annotations

import logging
import time

from ..config import get_settings
from ..enums import Provider
from .base import (
    BaseProvider,
    GenerationRequest,
    GenerationResult,
    ModelCapabilities,
    ProviderError,
    ProviderNotConfigured,
)
from .catalog import find_seed

log = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    name = Provider.ANTHROPIC

    def __init__(self) -> None:
        self._client = None

    # -- client ------------------------------------------------------------

    def _get_client(self):
        if self._client is not None:
            return self._client
        settings = get_settings()
        if not settings.has_anthropic:
            raise ProviderNotConfigured("anthropic")
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise ProviderError(
                "The 'anthropic' package is not installed. Run: pip install anthropic",
                error_type="sdk_missing",
            ) from exc
        self._client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
            timeout=settings.provider_timeout_seconds,
            max_retries=settings.provider_max_retries,
        )
        return self._client

    # -- capabilities ------------------------------------------------------

    def capabilities(self, model_id: str) -> ModelCapabilities:
        seed = find_seed(Provider.ANTHROPIC.value, model_id)
        if seed:
            return ModelCapabilities(
                supports_temperature=seed.supports_temperature,
                supports_effort=seed.supports_effort,
                supports_max_output_tokens=seed.supports_max_output_tokens,
                supports_structured_output=seed.supports_structured_output,
                default_effort=seed.default_effort,
            )
        # Unknown model: assume the current-generation shape (no sampling
        # control) so we never send a parameter that returns 400.
        return ModelCapabilities(
            supports_temperature=False,
            supports_effort=True,
            supports_max_output_tokens=True,
            supports_structured_output=True,
            default_effort=None,
        )

    def list_models(self) -> list[str]:
        client = self._get_client()
        try:
            return [m.id for m in client.models.list()]
        except Exception as exc:  # pragma: no cover - network dependent
            raise ProviderError(
                f"Could not list Anthropic models: {exc}", error_type="model_list_failed"
            ) from exc

    # -- generation --------------------------------------------------------

    def generate(self, model_id: str, request: GenerationRequest) -> GenerationResult:
        client = self._get_client()
        caps = self.capabilities(model_id)
        effective, limitations = self.reconcile_settings(request, caps)

        kwargs: dict = {
            "model": model_id,
            "max_tokens": effective.get("max_output_tokens", request.max_output_tokens),
            "messages": [{"role": "user", "content": request.user}],
        }
        if request.system:
            kwargs["system"] = request.system
        if "temperature" in effective:
            kwargs["temperature"] = effective["temperature"]

        output_config: dict = {}
        if "effort" in effective:
            output_config["effort"] = effective["effort"]
        if request.json_schema is not None and caps.supports_structured_output:
            output_config["format"] = {
                "type": "json_schema",
                "schema": request.json_schema,
            }
        if output_config:
            kwargs["output_config"] = output_config

        started = time.perf_counter()
        response = self._create_with_degradation(client, kwargs, limitations)
        latency_ms = int((time.perf_counter() - started) * 1000)

        # A refusal is a real outcome, not a crash: report it rather than
        # returning an empty explanation that looks like a model failure.
        stop_reason = getattr(response, "stop_reason", None)
        if stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            category = getattr(details, "category", None) if details else None
            raise ProviderError(
                f"Anthropic declined this request (category={category!r}).",
                error_type="refusal",
            )

        text = "".join(
            block.text
            for block in (response.content or [])
            if getattr(block, "type", None) == "text"
        ).strip()

        if stop_reason == "max_tokens":
            limitations.append(
                "Output hit max_tokens and was truncated mid-explanation; "
                "raise the token limit before using this response as a stimulus."
            )

        usage = getattr(response, "usage", None)
        return GenerationResult(
            text=text,
            provider=Provider.ANTHROPIC.value,
            model_id=model_id,
            input_tokens=getattr(usage, "input_tokens", None) if usage else None,
            output_tokens=getattr(usage, "output_tokens", None) if usage else None,
            latency_ms=latency_ms,
            finish_reason=stop_reason,
            control_limitations=limitations,
            effective_settings=effective,
        )

    def _create_with_degradation(self, client, kwargs: dict, limitations: list[str]):
        """Call the API, retrying once without a parameter the model rejects.

        Capability drift between model generations is the norm, not the
        exception. When a parameter is rejected we remove it, record the fact as
        a control limitation, and retry once — rather than failing the whole
        batch or silently switching model.
        """
        attempt_kwargs = dict(kwargs)
        for _ in range(3):
            try:
                return client.messages.create(**attempt_kwargs)
            except Exception as exc:
                message = str(exc)
                status = getattr(exc, "status_code", None)
                if status != 400:
                    raise ProviderError(
                        f"Anthropic request failed: {message}",
                        error_type=type(exc).__name__,
                        status=status,
                    ) from exc
                removed = self._strip_rejected_param(attempt_kwargs, message, limitations)
                if not removed:
                    raise ProviderError(
                        f"Anthropic rejected the request: {message}",
                        error_type="invalid_request",
                        status=400,
                    ) from exc
        raise ProviderError(
            "Anthropic rejected the request after removing unsupported parameters.",
            error_type="invalid_request",
        )

    @staticmethod
    def _strip_rejected_param(kwargs: dict, message: str, limitations: list[str]) -> bool:
        lowered = message.lower()
        if "temperature" in lowered and "temperature" in kwargs:
            kwargs.pop("temperature")
            limitations.append(
                "Provider rejected `temperature`; retried without it. Generation "
                "conditions are not temperature-controlled for this model."
            )
            return True
        oc = kwargs.get("output_config") or {}
        if "effort" in lowered and "effort" in oc:
            oc.pop("effort")
            limitations.append("Provider rejected `effort`; retried without it.")
            if not oc:
                kwargs.pop("output_config", None)
            return True
        if ("format" in lowered or "schema" in lowered) and "format" in oc:
            oc.pop("format")
            limitations.append(
                "Provider rejected structured output; retried with the schema described "
                "in the prompt and defensive JSON parsing."
            )
            if not oc:
                kwargs.pop("output_config", None)
            return True
        return False
