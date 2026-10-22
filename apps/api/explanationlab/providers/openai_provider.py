"""OpenAI Responses API adapter."""

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


class OpenAIProvider(BaseProvider):
    name = Provider.OPENAI

    def __init__(self) -> None:
        self._client = None

    # -- client ------------------------------------------------------------

    def _get_client(self):
        if self._client is not None:
            return self._client
        settings = get_settings()
        if not settings.has_openai:
            raise ProviderNotConfigured("openai")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise ProviderError(
                "The 'openai' package is not installed. Run: pip install openai",
                error_type="sdk_missing",
            ) from exc
        self._client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.provider_timeout_seconds,
            max_retries=settings.provider_max_retries,
        )
        return self._client

    # -- capabilities ------------------------------------------------------

    def capabilities(self, model_id: str) -> ModelCapabilities:
        seed = find_seed(Provider.OPENAI.value, model_id)
        if seed:
            return ModelCapabilities(
                supports_temperature=seed.supports_temperature,
                supports_effort=seed.supports_effort,
                supports_max_output_tokens=seed.supports_max_output_tokens,
                supports_structured_output=seed.supports_structured_output,
                default_effort=seed.default_effort,
            )
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
                f"Could not list OpenAI models: {exc}", error_type="model_list_failed"
            ) from exc

    # -- generation --------------------------------------------------------

    def generate(self, model_id: str, request: GenerationRequest) -> GenerationResult:
        client = self._get_client()
        caps = self.capabilities(model_id)
        effective, limitations = self.reconcile_settings(request, caps)

        messages: list[dict] = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.user})

        kwargs: dict = {"model": model_id, "input": messages}
        if "max_output_tokens" in effective:
            kwargs["max_output_tokens"] = effective["max_output_tokens"]
        if "temperature" in effective:
            kwargs["temperature"] = effective["temperature"]
        if "effort" in effective:
            kwargs["reasoning"] = {"effort": effective["effort"]}
        if request.json_schema is not None and caps.supports_structured_output:
            kwargs["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": request.json_schema_name,
                    "strict": False,
                    "schema": request.json_schema,
                }
            }

        started = time.perf_counter()
        response = self._create_with_degradation(client, kwargs, limitations)
        latency_ms = int((time.perf_counter() - started) * 1000)

        text = (getattr(response, "output_text", "") or "").strip()
        status = getattr(response, "status", None)

        if not text:
            refusal = self._find_refusal(response)
            if refusal:
                raise ProviderError(
                    f"OpenAI declined this request: {refusal}", error_type="refusal"
                )

        if status == "incomplete":
            details = getattr(response, "incomplete_details", None)
            reason = getattr(details, "reason", None) if details else None
            limitations.append(
                f"Response incomplete (reason={reason!r}); the explanation may be truncated."
            )

        usage = getattr(response, "usage", None)
        return GenerationResult(
            text=text,
            provider=Provider.OPENAI.value,
            model_id=model_id,
            input_tokens=getattr(usage, "input_tokens", None) if usage else None,
            output_tokens=getattr(usage, "output_tokens", None) if usage else None,
            latency_ms=latency_ms,
            finish_reason=status,
            control_limitations=limitations,
            effective_settings=effective,
        )

    @staticmethod
    def _find_refusal(response) -> str | None:
        for item in getattr(response, "output", None) or []:
            for block in getattr(item, "content", None) or []:
                if getattr(block, "type", None) == "refusal":
                    return getattr(block, "refusal", "refused")
        return None

    def _create_with_degradation(self, client, kwargs: dict, limitations: list[str]):
        """As with Anthropic: strip a rejected parameter, record it, retry once."""
        attempt_kwargs = dict(kwargs)
        for _ in range(3):
            try:
                return client.responses.create(**attempt_kwargs)
            except Exception as exc:
                message = str(exc)
                status = getattr(exc, "status_code", None)
                if status != 400:
                    raise ProviderError(
                        f"OpenAI request failed: {message}",
                        error_type=type(exc).__name__,
                        status=status,
                    ) from exc
                if not self._strip_rejected_param(attempt_kwargs, message, limitations):
                    raise ProviderError(
                        f"OpenAI rejected the request: {message}",
                        error_type="invalid_request",
                        status=400,
                    ) from exc
        raise ProviderError(
            "OpenAI rejected the request after removing unsupported parameters.",
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
        if "reasoning" in lowered and "reasoning" in kwargs:
            kwargs.pop("reasoning")
            limitations.append("Provider rejected `reasoning.effort`; retried without it.")
            return True
        if ("text" in lowered or "schema" in lowered or "format" in lowered) and "text" in kwargs:
            kwargs.pop("text")
            limitations.append(
                "Provider rejected structured output; retried with the schema described "
                "in the prompt and defensive JSON parsing."
            )
            return True
        return False
