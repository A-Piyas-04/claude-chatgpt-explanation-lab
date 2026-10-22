"""Google Gemini generateContent adapter for real text and JSON calls."""

from __future__ import annotations

import time
from urllib.parse import quote

import httpx

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

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(BaseProvider):
    name = Provider.GEMINI

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client

    def _get_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        settings = get_settings()
        if not settings.has_gemini:
            raise ProviderNotConfigured("gemini")
        self._client = httpx.Client(
            base_url=API_ROOT,
            headers={"x-goog-api-key": settings.gemini_api_key},
            timeout=settings.provider_timeout_seconds,
        )
        return self._client

    def capabilities(self, model_id: str) -> ModelCapabilities:
        return ModelCapabilities(
            supports_temperature=True,
            supports_effort=False,
            supports_max_output_tokens=True,
            supports_structured_output=True,
        )

    def list_models(self) -> list[str]:
        client = self._get_client()
        models: list[str] = []
        page_token: str | None = None
        try:
            while True:
                response = client.get("/models", params={"pageToken": page_token} if page_token else {})
                self._raise_for_status(response)
                payload = response.json()
                for model in payload.get("models", []):
                    model_id = str(model.get("name", "")).removeprefix("models/")
                    methods = model.get("supportedGenerationMethods", [])
                    if model_id.startswith("gemini-") and "generateContent" in methods:
                        if not any(tag in model_id for tag in ("-image", "-tts", "-audio", "-live")):
                            models.append(model_id)
                page_token = payload.get("nextPageToken")
                if not page_token:
                    break
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(
                f"Could not list Gemini models: {exc}", error_type="model_list_failed"
            ) from exc
        return models

    def generate(self, model_id: str, request: GenerationRequest) -> GenerationResult:
        client = self._get_client()
        effective, limitations = self.reconcile_settings(request, self.capabilities(model_id))
        config: dict = {"maxOutputTokens": effective["max_output_tokens"]}
        if "temperature" in effective:
            config["temperature"] = effective["temperature"]
        if request.json_schema is not None:
            config["responseMimeType"] = "application/json"
            config["responseJsonSchema"] = request.json_schema

        body: dict = {
            "contents": [{"role": "user", "parts": [{"text": request.user}]}],
            "generationConfig": config,
        }
        if request.system:
            body["systemInstruction"] = {"parts": [{"text": request.system}]}

        started = time.perf_counter()
        url = f"/models/{quote(model_id, safe='')}:generateContent"
        try:
            response = client.post(url, json=body)
            if response.status_code == 400 and request.json_schema is not None:
                # Some otherwise usable models reject a particular JSON Schema.
                # Keep JSON mode, but make the loss of schema enforcement visible.
                config.pop("responseJsonSchema")
                limitations.append(
                    "Gemini rejected the JSON schema; retried in JSON mode without schema enforcement."
                )
                response = client.post(url, json=body)
            self._raise_for_status(response)
            payload = response.json()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Gemini request failed: {exc}", error_type="network_error") from exc
        except ValueError as exc:
            raise ProviderError("Gemini returned invalid JSON.", error_type="invalid_response") from exc

        candidates = payload.get("candidates") or []
        candidate = candidates[0] if candidates else {}
        parts = (candidate.get("content") or {}).get("parts") or []
        output = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
        finish_reason = candidate.get("finishReason")
        if not output:
            reason = finish_reason or (payload.get("promptFeedback") or {}).get("blockReason")
            raise ProviderError(
                f"Gemini returned no text (reason: {reason or 'unknown'}).",
                error_type="empty_response",
            )
        if finish_reason == "MAX_TOKENS":
            limitations.append("Output reached maxOutputTokens and may be incomplete.")
        usage = payload.get("usageMetadata") or {}
        generated_tokens = usage.get("candidatesTokenCount")
        thought_tokens = usage.get("thoughtsTokenCount")
        output_tokens = (
            (generated_tokens or 0) + (thought_tokens or 0)
            if generated_tokens is not None or thought_tokens is not None
            else None
        )
        return GenerationResult(
            text=output,
            provider=Provider.GEMINI.value,
            model_id=model_id,
            input_tokens=usage.get("promptTokenCount"),
            output_tokens=output_tokens,
            latency_ms=int((time.perf_counter() - started) * 1000),
            finish_reason=finish_reason,
            control_limitations=limitations,
            effective_settings=effective,
        )

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.is_success:
            return
        try:
            error = response.json().get("error", {})
            message = error.get("message") or response.reason_phrase
        except ValueError:
            message = response.reason_phrase
        raise ProviderError(
            f"Gemini API returned HTTP {response.status_code}: {str(message)[:500]}",
            error_type="rate_limit" if response.status_code == 429 else "provider_error",
            status=response.status_code,
        )
