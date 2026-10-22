"""End-to-end test of the nine steps required by §16 of the brief.

Runs through the HTTP API in demo mode: no credentials, no network, no spend.

    1. Researcher creates a question
    2. Researcher configures a baseline experiment
    3. App generates two model responses
    4. Responses appear in the comparison view
    5. Researcher runs a transformation
    6. Transformed response is persisted
    7. Researcher creates a blind evaluation study
    8. Participant submits an assessment
    9. Dashboard displays the stored result
"""

from __future__ import annotations

from explanationlab.jobs.worker import run_job


def _drain_jobs(client, job_id: str) -> dict:
    """Execute a queued job synchronously (the in-API worker is off in tests)."""
    run_job(job_id)
    return client.get(f"/api/jobs/{job_id}").json()


def test_full_researcher_and_participant_journey(client):
    # -- 1. Create a research question ------------------------------------
    created = client.post(
        "/api/questions",
        json={
            "text": "How does a write-through cache differ from a write-back cache?",
            "domain": "software_engineering",
            "topic": "caching",
            "conceptual_difficulty": "moderate",
            "factual_checklist": [
                "A write-through cache writes to cache and backing store together.",
                "A write-back cache defers the write to the backing store.",
                "Write-back risks data loss if the cache fails before flushing.",
            ],
        },
    )
    assert created.status_code == 201
    question = created.json()
    assert question["factual_checklist"]

    profiles = client.get("/api/learner-profiles").json()
    profile_id = next(p["id"] for p in profiles if p["level"] == "intermediate")

    # -- 2. Configure a baseline experiment -------------------------------
    spec = {
        "name": "E2E baseline comparison",
        "type": "baseline",
        "question_ids": [question["id"]],
        "source_models": [
            {"provider": "openai", "model_id": "gpt-6.1-sol"},
            {"provider": "anthropic", "model_id": "claude-sonnet-5-5"},
        ],
        "learner_profile_id": profile_id,
        "objective": "Compare default explanation styles.",
        "hypothesis": "H1 — default behavioural alignment differs.",
    }

    estimate = client.post("/api/experiments/estimate", json=spec)
    assert estimate.status_code == 200
    assert estimate.json()["total_model_calls"] == 2

    experiment = client.post("/api/experiments", json=spec)
    assert experiment.status_code == 201
    experiment_id = experiment.json()["id"]
    assert experiment.json()["status"] == "configured"

    # -- 3. Generate two model responses ----------------------------------
    run = client.post(
        f"/api/experiments/{experiment_id}/run", json={"confirm_cost": True}
    )
    assert run.status_code == 202
    job = _drain_jobs(client, run.json()["id"])
    assert job["status"] == "succeeded", job
    assert job["progress_done"] == 2

    detail = client.get(f"/api/experiments/{experiment_id}").json()
    assert detail["run_counts"].get("succeeded") == 2

    # A duplicate submission is refused rather than re-billed.
    assert client.post(
        f"/api/experiments/{experiment_id}/run", json={"confirm_cost": True}
    ).status_code == 409

    # -- 4. Responses appear in the comparison view ------------------------
    responses = client.get(
        "/api/responses", params={"question_id": question["id"]}
    ).json()
    assert len(responses) == 2
    models = {r["model_id"] for r in responses}
    assert models == {"gpt-6.1-sol", "claude-sonnet-5-5"}
    # Demo mode: every response is flagged synthetic for its whole life.
    assert all(r["is_synthetic"] for r in responses)
    assert all(r["origin"] == "demo_fixture" for r in responses)

    source = responses[0]
    source_detail = client.get(f"/api/responses/{source['id']}").json()
    assert source_detail["automated_diagnostics"]["metrics"]["surface"]["word_count"] > 0
    assert (
        source_detail["automated_diagnostics"]["evidence_class"] == "automated_diagnostic"
    )
    assert source_detail["question"]["factual_checklist"]

    # Researcher annotation of explanation characteristics.
    assert client.post(
        f"/api/responses/{source['id']}/annotations",
        json={"label": "dense", "body": "Several ideas per sentence.", "author": "me"},
    ).status_code == 201

    # -- 5. Run a transformation -------------------------------------------
    transform = client.post(
        f"/api/responses/{source['id']}/transform",
        json={
            "treatments": ["T1", "T5"],
            "provider": "anthropic",
            "model_id": "claude-sonnet-5-5",
            "run_analysis": True,
            "run_planning": True,
            "run_fidelity": True,
            "save_variant": True,
        },
    )
    assert transform.status_code == 201, transform.json()
    result = transform.json()

    assert result["applied_treatments"] == ["T1", "T5"]
    assert len(result["changes"]) == 2
    # Each treatment reports measured, model-free change statistics.
    assert "word_similarity" in result["changes"][0]["stats"]
    assert result["analysis"] is not None
    assert result["plan"] is not None
    # Fidelity is always provisional, never "verified".
    assert result["fidelity"]["provisional"] is True
    # Pipeline stages are recorded for cost/latency accounting.
    assert {s["stage"] for s in result["stages"]} == {"A", "B", "C", "D"}

    # -- 6. Transformed response is persisted ------------------------------
    variant_id = result["variant_response_id"]
    assert variant_id
    variant_detail = client.get(f"/api/responses/{variant_id}").json()
    variant = variant_detail["response"]

    assert variant["kind"] == "transformed"
    assert variant["parent_response_id"] == source["id"]
    assert variant["applied_treatments"] == ["T1", "T5"]
    # Synthetic provenance is inherited by the derived row.
    assert variant["is_synthetic"] is True
    # Provenance chain back to the raw output is intact.
    assert variant_detail["source_response"]["id"] == source["id"]
    assert variant_detail["source_response"]["text"] == source["text"]
    assert variant_detail["transformation_meta"]["source_response_id"] == source["id"]
    assert variant_detail["fidelity_reports"]
    assert variant_detail["automated_diagnostics"]["metrics"]

    # Concept dependency graph, labelled as a hypothesis.
    graph = client.post(
        f"/api/responses/{source['id']}/concept-graph",
        params={"provider": "anthropic", "model_id": "claude-sonnet-5-5"},
    )
    assert graph.status_code == 201
    graph_payload = graph.json()
    assert graph_payload["nodes"]
    assert graph_payload["is_hypothesis"] is True
    assert "hypothesis" in graph_payload["disclaimer"]
    assert "violation_count" in graph_payload["sequencing_analysis"]

    # AI judge opinion, queued and blinded.
    judge = client.post(
        "/api/responses/judge",
        json={
            "provider": "openai",
            "model_id": "gpt-6-luna",
            "response_ids": [source["id"], variant_id],
        },
    )
    assert judge.status_code == 201
    judge_job = _drain_jobs(client, judge.json()["job_id"])
    assert judge_job["status"] == "succeeded", judge_job

    judged = client.get(f"/api/responses/{variant_id}").json()
    assert judged["ai_judge_evaluations"]
    assert judged["ai_judge_evaluations"][0]["blinded"] is True
    assert judged["ai_judge_evaluations"][0]["evidence_class"] == "ai_judge_opinion"

    # -- 7. Create a blinded human evaluation study ------------------------
    study = client.post(
        "/api/studies",
        json={
            "name": "E2E comprehension study",
            "question_id": question["id"],
            "response_ids": [source["id"], variant_id],
            "items": [
                {
                    "format": "multiple_choice",
                    "dimension": "A_immediate_comprehension",
                    "prompt": "Which statement matches the explanation?",
                    "options": [
                        "Write-back defers the write to the backing store.",
                        "Write-back writes to both at the same time.",
                        "Write-back never writes to the backing store.",
                    ],
                    "correct_option_index": 0,
                    "misconception_option_indexes": [2],
                    "max_score": 1.0,
                },
                {
                    "format": "short_answer",
                    "dimension": "B_mechanistic_understanding",
                    "prompt": "In your own words, why does write-back risk data loss?",
                    "rubric_key": "mechanism_short_answer",
                    "max_score": 2.0,
                },
                {
                    "format": "scenario",
                    "dimension": "C_transfer",
                    "prompt": "A server loses power. Which cache type loses data, and why?",
                    "rubric_key": "transfer_scenario",
                    "max_score": 2.0,
                },
            ],
        },
    )
    assert study.status_code == 201, study.json()
    study_id = study.json()["id"]
    token = study.json()["access_token"]

    opened = client.post(f"/api/studies/{study_id}/status", json={"status": "open"})
    assert opened.status_code == 200

    study_detail = client.get(f"/api/studies/{study_id}").json()
    assert len(study_detail["conditions"]) == 2
    assert study_detail["participant_url_path"] == f"/p/{token}"

    # -- 8. Participant submits an assessment ------------------------------
    intro = client.get(f"/api/p/{token}").json()
    assert intro["study_name"] == "E2E comprehension study"
    assert "withdraw" in intro["consent_text"].lower()
    # The explanation is not served before consent.
    assert "explanation" not in intro

    entered = client.post(
        f"/api/p/{token}/enter",
        json={"consent_given": True, "self_reported_level": "intermediate"},
    )
    assert entered.status_code == 201
    session = entered.json()
    participant_code = session["participant_code"]

    # Blinding: nothing identifying the condition reaches the participant.
    assert session["explanation"]["text"]
    assert set(session["explanation"].keys()) == {"text"}
    serialised = str(session)
    for leak in ("gpt-6.1-sol", "claude-sonnet-5-5", "openai", "anthropic", "T1", "T5"):
        assert leak not in serialised, f"participant payload leaked {leak!r}"
    # Answer keys are stripped from items.
    assert all("correct_option_index" not in item for item in session["items"])

    answers = []
    for item in session["items"]:
        if item["format"] == "multiple_choice":
            answers.append(
                {"item_id": item["id"], "selected_option_index": 0, "seconds_spent": 12.0}
            )
        else:
            answers.append(
                {
                    "item_id": item["id"],
                    "text_answer": "Because the write is deferred, so unflushed data is lost.",
                    "seconds_spent": 45.0,
                }
            )

    submitted = client.post(
        f"/api/p/{token}/submit",
        json={
            "participant_code": participant_code,
            "answers": answers,
            "reading_seconds": 180.0,
            "assessment_seconds": 110.0,
            "clarity_rating": 5,
            "cognitive_effort_rating": 3,
            "free_text_feedback": "The middle section was hard to follow.",
        },
    )
    assert submitted.status_code == 201
    # No score is returned to the participant.
    assert "score" not in submitted.json()

    # Re-submission and repeat exposure are both refused.
    assert client.post(
        f"/api/p/{token}/submit",
        json={"participant_code": participant_code, "answers": answers},
    ).status_code == 409
    assert client.post(
        f"/api/p/{token}/enter",
        json={"consent_given": True, "participant_code": participant_code},
    ).status_code == 409

    # -- 9. Results are stored and surfaced --------------------------------
    submissions = client.get(f"/api/studies/{study_id}/submissions").json()
    assert len(submissions) == 1
    items = submissions[0]["items"]

    mcq = next(i for i in items if i["format"] == "multiple_choice")
    assert mcq["auto_score"] == 1.0, "objective items are scored on submission"
    free_items = [i for i in items if i["format"] in {"short_answer", "scenario"}]
    assert all(i["needs_grading"] for i in free_items), "free text awaits a human"
    assert all(i["final_score"] is None for i in free_items)

    results_before = client.get(f"/api/studies/{study_id}/results").json()
    assert results_before["totals"]["submitted"] == 1
    assert results_before["totals"]["pending_grading_items"] == 2
    assert any("not yet graded" in w for w in results_before["warnings"])

    # A human grades the free-text answers; that score is authoritative.
    for item in free_items:
        graded = client.post(
            f"/api/item-responses/{item['item_response_id']}/grade",
            json={
                "human_score": 2.0,
                "misconception_detected": False,
                "grader_notes": "Correct causal account.",
            },
        )
        assert graded.status_code == 200
        assert graded.json()["final_score"] == 2.0

    results = client.get(f"/api/studies/{study_id}/results").json()
    assert results["totals"]["pending_grading_items"] == 0
    submitted_arm = next(
        c for c in results["conditions"] if c["participants"]["submitted"] == 1
    )
    comprehension = submitted_arm["human_comprehension"]
    assert comprehension["evidence_class"] == "human_comprehension"
    assert comprehension["overall"]["mean"] == 1.0  # 5 of 5 points
    # n=1, so no interval is fabricated.
    assert comprehension["overall"]["ci_low"] is None
    # Perceived clarity is reported separately, never folded in.
    assert submitted_arm["human_preference"]["perceived_clarity"]["mean"] == 5.0
    assert submitted_arm["human_preference"]["evidence_class"] == "human_preference"
    assert "exploratory" in " ".join(results["warnings"])
    assert results["contains_synthetic_data"] is True

    # Dashboard reflects real stored counts.
    overview = client.get("/api/analytics/overview").json()
    assert overview["experiments"]["total"] >= 1
    assert overview["human_studies"]["submissions"] >= 1
    assert overview["responses"]["synthetic"] >= 2
    assert overview["contains_synthetic_data"] is True
    assert overview["evaluation_coverage"]["responses_with_judge_opinion"] >= 1

    # Usage, cost and errors are inspectable.
    usage = client.get("/api/usage").json()
    assert "spend_controls" in usage
    assert usage["spend_controls"]["daily_cap_usd"] > 0

    # -- Exports -----------------------------------------------------------
    csv_export = client.get(
        f"/api/experiments/{experiment_id}/export", params={"format": "csv"}
    )
    assert csv_export.status_code == 200
    assert "response_id" in csv_export.text
    assert "SYNTHETIC" in csv_export.text

    json_export = client.get(
        f"/api/experiments/{experiment_id}/export", params={"format": "json"}
    ).json()
    assert json_export["contains_synthetic_data"] is True
    assert json_export["experiment"]["seed"]
    assert json_export["responses"][0]["system_prompt_snapshot"]

    md_export = client.get(
        f"/api/experiments/{experiment_id}/export", params={"format": "markdown"}
    )
    assert "## Limitations" in md_export.text

    report = client.post(f"/api/experiments/{experiment_id}/report")
    assert report.status_code == 201
    assert report.json()["contains_synthetic_data"] is True

    study_report = client.post(f"/api/studies/{study_id}/report")
    assert study_report.status_code == 201
    assert "primary evidence" in study_report.json()["body_markdown"]

    study_csv = client.get(f"/api/studies/{study_id}/export", params={"format": "csv"})
    assert "participant_code" in study_csv.text
    assert "perceived clarity is NOT comprehension" in study_csv.text


def test_participant_can_withdraw_and_data_is_deleted(client):
    """Withdrawal deletes the submission rather than flagging it."""
    question = client.post(
        "/api/questions",
        json={"text": "Why is a p-value easy to misread?", "domain": "statistics"},
    ).json()

    spec = {
        "name": "Withdrawal study source",
        "type": "baseline",
        "question_ids": [question["id"]],
        "source_models": [
            {"provider": "openai", "model_id": "gpt-6.1-sol"},
            {"provider": "anthropic", "model_id": "claude-haiku-5-5"},
        ],
    }
    experiment_id = client.post("/api/experiments", json=spec).json()["id"]
    job = client.post(
        f"/api/experiments/{experiment_id}/run", json={"confirm_cost": True}
    ).json()
    _drain_jobs(client, job["id"])

    responses = client.get(
        "/api/responses", params={"question_id": question["id"]}
    ).json()
    study = client.post(
        "/api/studies",
        json={
            "name": "Withdrawal test",
            "question_id": question["id"],
            "response_ids": [responses[0]["id"], responses[1]["id"]],
            "items": [
                {
                    "format": "multiple_choice",
                    "dimension": "A_immediate_comprehension",
                    "prompt": "Pick one.",
                    "options": ["a", "b"],
                    "correct_option_index": 0,
                }
            ],
        },
    ).json()
    client.post(f"/api/studies/{study['id']}/status", json={"status": "open"})
    token = study["access_token"]

    session = client.post(f"/api/p/{token}/enter", json={"consent_given": True}).json()
    code = session["participant_code"]
    item_id = session["items"][0]["id"]

    client.post(
        f"/api/p/{token}/submit",
        json={
            "participant_code": code,
            "answers": [{"item_id": item_id, "selected_option_index": 0}],
            "clarity_rating": 4,
        },
    )
    assert client.get(f"/api/studies/{study['id']}/results").json()["totals"]["submitted"] == 1

    withdrawn = client.post(
        f"/api/p/{token}/withdraw", json={"participant_code": code}
    )
    assert withdrawn.status_code == 200
    assert "deleted" in withdrawn.json()["message"]

    after = client.get(f"/api/studies/{study['id']}/results").json()
    assert after["totals"]["submitted"] == 0, "withdrawn data must be gone, not hidden"


def test_study_requires_same_question_across_conditions(client):
    """Comparing explanations of different questions would be confounded."""
    q1 = client.post("/api/questions", json={"text": "First distinct question?"}).json()
    q2 = client.post("/api/questions", json={"text": "Second distinct question?"}).json()

    ids = []
    for question in (q1, q2):
        experiment_id = client.post(
            "/api/experiments",
            json={
                "name": f"src {question['id'][:6]}",
                "type": "baseline",
                "question_ids": [question["id"]],
                "source_models": [{"provider": "openai", "model_id": "gpt-6.1-sol"}],
            },
        ).json()["id"]
        job = client.post(
            f"/api/experiments/{experiment_id}/run", json={"confirm_cost": True}
        ).json()
        _drain_jobs(client, job["id"])
        ids.append(
            client.get("/api/responses", params={"question_id": question["id"]}).json()[0][
                "id"
            ]
        )

    refused = client.post(
        "/api/studies",
        json={"name": "Confounded", "response_ids": ids, "items": []},
    )
    assert refused.status_code == 422
    assert "same research question" in refused.json()["detail"]


def test_study_cannot_open_without_items_or_enough_arms(client):
    question = client.post("/api/questions", json={"text": "Gate check question?"}).json()
    experiment_id = client.post(
        "/api/experiments",
        json={
            "name": "gate src",
            "type": "baseline",
            "question_ids": [question["id"]],
            "source_models": [
                {"provider": "openai", "model_id": "gpt-6.1-sol"},
                {"provider": "anthropic", "model_id": "claude-haiku-5-5"},
            ],
        },
    ).json()["id"]
    job = client.post(
        f"/api/experiments/{experiment_id}/run", json={"confirm_cost": True}
    ).json()
    _drain_jobs(client, job["id"])
    responses = client.get(
        "/api/responses", params={"question_id": question["id"]}
    ).json()

    study = client.post(
        "/api/studies",
        json={
            "name": "No items",
            "response_ids": [responses[0]["id"], responses[1]["id"]],
            "items": [],
        },
    ).json()

    refused = client.post(f"/api/studies/{study['id']}/status", json={"status": "open"})
    assert refused.status_code == 422
    assert "assessment item" in refused.json()["detail"]


def test_invalid_study_token_is_indistinguishable_from_a_closed_study(client):
    assert client.get("/api/p/not-a-real-token").status_code == 404


def test_three_prompt_conditions_run_as_one_experiment(client):
    """Experiment 2: conditions A, B and C over one question."""
    question = client.post(
        "/api/questions",
        json={"text": "How does a message queue improve reliability for real?"},
    ).json()

    spec = {
        "name": "E2E prompt intervention",
        "type": "prompt_intervention",
        "question_ids": [question["id"]],
        "source_models": [{"provider": "anthropic", "model_id": "claude-sonnet-5-5"}],
        "prompt_template_keys": [
            "condition_a_default",
            "condition_b_generic_tutor",
            "condition_c_structured_pedagogical",
        ],
    }
    experiment_id = client.post("/api/experiments", json=spec).json()["id"]
    job = client.post(
        f"/api/experiments/{experiment_id}/run", json={"confirm_cost": True}
    ).json()
    assert _drain_jobs(client, job["id"])["status"] == "succeeded"

    detail = client.get(f"/api/experiments/{experiment_id}").json()
    assert len(detail["conditions"]) == 3
    assert detail["run_counts"].get("succeeded") == 3

    summary = client.get(f"/api/analytics/experiments/{experiment_id}").json()
    assert len(summary["conditions"]) == 3
    # Each arm used a different prompt version, and the fixtures differ by
    # condition, so the diagnostics differ too.
    word_counts = {
        c["label"]: c["automated_diagnostics"]["metrics"]["word_count"]["mean"]
        for c in summary["conditions"]
    }
    assert len(set(word_counts.values())) > 1
    assert "comprehension" in summary["evidence_note"]


def test_ablation_experiment_isolates_single_treatments(client):
    """Experiment 3: one arm per treatment, plus an untransformed control."""
    question = client.post(
        "/api/questions", json={"text": "Why do race conditions appear intermittently?"}
    ).json()

    spec = {
        "name": "E2E ablation",
        "type": "ablation",
        "question_ids": [question["id"]],
        "source_models": [{"provider": "anthropic", "model_id": "claude-haiku-5-5"}],
        "treatment_sets": [["T1"], ["T5"], ["T1", "T5"]],
        "run_analysis": False,
        "run_planning": False,
        "include_untransformed_control": True,
    }
    experiment_id = client.post("/api/experiments", json=spec).json()["id"]
    job = client.post(
        f"/api/experiments/{experiment_id}/run", json={"confirm_cost": True}
    ).json()
    assert _drain_jobs(client, job["id"])["status"] == "succeeded"

    summary = client.get(f"/api/analytics/experiments/{experiment_id}").json()
    treatment_sets = {tuple(c["treatments"]) for c in summary["conditions"]}
    assert treatment_sets == {(), ("T1",), ("T5",), ("T1", "T5")}

    # Cost and latency per technique is answerable.
    tradeoff = client.get(
        "/api/analytics/cost-latency", params={"include_synthetic": True}
    ).json()
    keys = {g["treatments"] for g in tradeoff["groups"]}
    assert "T1" in keys and "T1+T5" in keys


def test_demo_mode_is_declared_and_cannot_be_mistaken_for_real_data(client):
    status = client.get("/api/status").json()
    assert status["demo_mode"] is True
    assert "synthetic" in status["demo_mode_notice"].lower()
    assert "DEMO MODE" in status["demo_mode_notice"]
    assert status["providers"]["openai"]["configured"] is False
    # No secret ever appears in the status payload.
    assert "api_key" not in str(status).lower()

    breakdown = client.get(
        "/api/analytics/breakdown", params={"group_by": "model", "metric": "word_count"}
    ).json()
    # Synthetic rows are excluded from the dashboard by default.
    assert breakdown["include_synthetic"] is False
    assert breakdown["groups"] == []
