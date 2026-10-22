"""Gemini adapter contract without a network call or an API key."""

from __future__ import annotations

import httpx
import pytest

from explanationlab.config import Settings
from explanationlab.providers import registry
from explanationlab.providers.base import GenerationRequest, ProviderError
from explanationlab.providers.gemini_provider import GeminiProvider


def _client(handler):
    return httpx.Client(
        base_url="https://generativelanguage.googleapis.com/v1beta",
        transport=httpx.MockTransport(handler),
    )


def test_gemini_generation_preserves_real_provenance_and_usage():
    def handle(request):
        assert request.url.path.endswith("/models/gemini-3.5-flash-lite:generateContent")
        payload = __import__("json").loads(request.content)
        assert payload["systemInstruction"]["parts"][0]["text"] == "Explain clearly"
        assert payload["contents"][0]["parts"][0]["text"] == "What is a cache?"
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "A cache stores copies."}]},
                                "finishReason": "STOP"}],
                "usageMetadata": {
                    "promptTokenCount": 12,
                    "candidatesTokenCount": 6,
                    "thoughtsTokenCount": 3,
                },
            },
        )

    provider = GeminiProvider(_client(handle))
    result = provider.generate(
        "gemini-3.5-flash-lite",
        GenerationRequest(system="Explain clearly", user="What is a cache?", effort="high"),
    )
    assert result.text == "A cache stores copies."
    assert result.input_tokens == 12 and result.output_tokens == 9
    assert result.is_synthetic is False
    assert any("effort" in note for note in result.control_limitations)


def test_gemini_json_schema_rejection_is_recorded_and_retried():
    calls = []

    def handle(request):
        payload = __import__("json").loads(request.content)
        calls.append(payload)
        if len(calls) == 1:
            return httpx.Response(400, json={"error": {"message": "Unsupported schema"}})
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]},
                                  "finishReason": "STOP"}]},
        )

    result = GeminiProvider(_client(handle)).generate(
        "gemini-3.5-flash-lite",
        GenerationRequest(system="", user="Return JSON", json_schema={"type": "object"}),
    )
    assert len(calls) == 2
    assert "responseJsonSchema" in calls[0]["generationConfig"]
    assert "responseJsonSchema" not in calls[1]["generationConfig"]
    assert any("without schema enforcement" in note for note in result.control_limitations)


def test_live_gemini_does_not_turn_missing_openai_into_fixture(monkeypatch):
    settings = Settings(
        _env_file=None, gemini_api_key="test", openai_api_key="", anthropic_api_key=""
    )
    monkeypatch.setattr(registry, "get_settings", lambda: settings)
    registry.reset_cache()
    assert registry.get_provider("gemini").name.value == "gemini"
    with pytest.raises(ProviderError, match="not configured"):
        registry.get_provider("openai")
    registry.reset_cache()


def test_imported_answer_labels_identify_study_arms_without_changing_model_id(client):
    question = client.post(
        "/api/questions",
        json={"text": "Explain how cache write policies differ.", "domain": "computing"},
    ).json()
    response_ids = []
    for label, provider, model in (
        ("ChatGPT web — original", "openai", "ChatGPT displayed model"),
        ("Claude web — original", "anthropic", "Claude displayed model"),
    ):
        imported = client.post(
            "/api/responses/import",
            json={
                "question_id": question["id"],
                "provider": provider,
                "model_id": model,
                "label": label,
                "text": "A real pasted explanation with enough text to import.",
            },
        )
        assert imported.status_code == 201
        assert imported.json()["model_id"] == model
        response_ids.append(imported.json()["id"])
    study = client.post(
        "/api/studies",
        json={"name": "Web answer comparison", "response_ids": response_ids},
    )
    assert study.status_code == 201
    detail = client.get(f"/api/studies/{study.json()['id']}").json()
    assert [condition["label"] for condition in detail["conditions"]] == [
        "ChatGPT web — original",
        "Claude web — original",
    ]
