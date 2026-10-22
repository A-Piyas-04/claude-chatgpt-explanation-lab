"""AI proxy runs on real imports and never creates a human submission."""

from __future__ import annotations

from explanationlab.evaluation import proxy


def test_proxy_audit_keeps_human_results_empty(client, monkeypatch):
    question = client.post(
        "/api/questions", json={"text": "Explain our project-specific cache protocol.", "domain": "computing"}
    ).json()
    text = "In the Lark protocol, amber writes are queued. Cobalt writes are committed at once."
    response_ids = []
    for provider, label in (("openai", "ChatGPT web"), ("anthropic", "Claude web")):
        response = client.post(
            "/api/responses/import",
            json={
                "question_id": question["id"], "provider": provider,
                "model_id": "Web model", "label": label, "text": text,
            },
        )
        assert response.status_code == 201
        response_ids.append(response.json()["id"])
    study = client.post(
        "/api/studies",
        json={
            "name": "Proxy separation test", "response_ids": response_ids,
            "items": [
                {
                    "format": "multiple_choice", "dimension": "A_immediate_comprehension",
                    "prompt": "Which color is queued in the Lark protocol?",
                    "options": ["Amber", "Cobalt"], "correct_option_index": 0,
                },
                {
                    "format": "multiple_choice", "dimension": "C_transfer",
                    "prompt": "Which color is committed immediately?",
                    "options": ["Amber", "Cobalt"], "correct_option_index": 1,
                },
            ],
        },
    )
    assert study.status_code == 201
    study_id = study.json()["id"]

    monkeypatch.setattr(proxy, "get_provider", lambda *args, **kwargs: object())
    calls = []

    def fake_ask(db, *, provider, model_id, items, explanation):
        calls.append(explanation)
        if explanation is None:
            return {
                items[0].id: {"selected_option_index": 1, "evidence_quote": ""},
                items[1].id: {"selected_option_index": 1, "evidence_quote": ""},
            }, 0.0
        return {
            items[0].id: {"selected_option_index": 0, "evidence_quote": "amber writes are queued"},
            items[1].id: {
                "selected_option_index": 1,
                "evidence_quote": "Cobalt writes are committed at once",
            },
        }, 0.0

    monkeypatch.setattr(proxy, "_ask", fake_ask)
    result = client.post(
        f"/api/studies/{study_id}/proxy-evaluation",
        json={"provider": "gemini", "model_id": "gemini-3.5-flash-lite"},
    )
    assert result.status_code == 201, result.text
    data = result.json()
    assert data["evidence_class"] == "ai_proxy_answerability"
    assert data["baseline_correct_count"] == 1
    assert data["diagnostic_item_count"] == 1
    assert [row["grounded_correct"] for row in data["conditions"]] == [2, 2]
    assert [row["diagnostic_grounded_correct"] for row in data["conditions"]] == [1, 1]
    assert calls == [None, text, text]
    assert client.get(f"/api/studies/{study_id}/proxy-evaluation").json()["id"] == data["id"]
    assert client.get(f"/api/studies/{study_id}").json()["participants"]["submitted"] == 0
    assert client.get(f"/api/studies/{study_id}/results").json()["totals"]["submitted"] == 0
