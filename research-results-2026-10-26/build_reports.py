"""Build human-readable and CSV summaries from saved experiment outputs."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import statistics
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
DB = ROOT / "apps/api/explanationlab.sqlite3"
TOPICS = ("caching", "databases", "tcp", "immunology", "interest")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def details(conn: sqlite3.Connection, response_id: str) -> dict:
    row = conn.execute("""
        SELECT r.id, r.provider, r.model_id, r.parent_response_id, r.label,
               r.question_id, r.applied_treatments, m.metrics
        FROM responses r JOIN text_metrics m ON m.response_id = r.id
        WHERE r.id = ?
    """, (response_id,)).fetchone()
    if row is None:
        raise ValueError(f"Missing response or metrics: {response_id}")
    obj = dict(row)
    obj["metrics"] = json.loads(obj["metrics"])
    return obj


def short_metrics(obj: dict) -> tuple[int, float, int]:
    m = obj["metrics"]
    return (
        m["surface"]["word_count"],
        m["surface"]["avg_sentence_words"],
        m["concept_coverage"]["covered"],
    )


def source_id(conn: sqlite3.Connection, topic: str, author: str) -> str:
    provider = "openai" if author == "chatgpt" else "anthropic"
    row = conn.execute("""
        SELECT r.id FROM responses r JOIN research_questions q ON q.id=r.question_id
        WHERE trim(q.topic, ' ' || char(9))=? AND r.provider=? AND r.origin='manual_import'
          AND lower(r.label) LIKE '%base%'
    """, (topic, provider)).fetchone()
    if row is None:
        raise ValueError((topic, author, "baseline missing"))
    return row[0]


def build_stage3(conn: sqlite3.Connection) -> list[dict]:
    rows = []
    for topic in TOPICS:
        for author in ("chatgpt", "claude"):
            baseline = details(conn, source_id(conn, topic, author))
            bw, bs, bc = short_metrics(baseline)
            for index in range(1, 7):
                treatment = f"T{index}"
                path = OUT / f"transform-{topic}-{author}-{treatment}.json"
                if not path.exists():
                    continue
                raw = load(path)
                variant = details(conn, raw["variant_response_id"])
                vw, vs, vc = short_metrics(variant)
                warnings = (raw.get("fidelity") or {}).get("warnings") or []
                rows.append({
                    "topic": topic,
                    "source_author": author,
                    "source_model": baseline["model_id"],
                    "treatment": treatment,
                    "source_response_id": baseline["id"],
                    "variant_response_id": variant["id"],
                    "fidelity_verdict": raw["fidelity"]["verdict"],
                    "warning_types": ";".join(w.get("type", "") for w in warnings),
                    "warning_detectors": ";".join(w.get("detector", "") for w in warnings),
                    "source_words": bw,
                    "variant_words": vw,
                    "word_delta": vw - bw,
                    "source_avg_sentence_words": bs,
                    "variant_avg_sentence_words": vs,
                    "source_lexical_checklist_matches": bc,
                    "variant_lexical_checklist_matches": vc,
                    "estimated_cost_usd": raw.get("total_cost_usd", 0),
                    "raw_file": path.name,
                })
    write_csv(OUT / "experiment-3-results.csv", rows)
    lines = [
        "# Experiment 3 - Single-treatment transformations",
        "",
        f"Saved runs: **{len(rows)}/60**. Each run used one treatment, Gemini 3.5 Flash-Lite, stages A/B/D, and saved a variant.",
        "",
        "| Treatment | Runs | Clean | Warnings | Serious concerns | Median word change |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    by_t = defaultdict(list)
    for row in rows:
        by_t[row["treatment"]].append(row)
    for treatment in (f"T{i}" for i in range(1, 7)):
        group = by_t[treatment]
        counts = Counter(row["fidelity_verdict"] for row in group)
        median = statistics.median([row["word_delta"] for row in group]) if group else 0
        lines.append(f"| {treatment} | {len(group)} | {counts['clean']} | {counts['warnings']} | {counts['serious_concerns']} | {median:+g} |")
    lines += [
        "",
        "## Interpretation",
        "",
        "A clean verdict means the automated audit detected no issue. It does not verify factual accuracy. Runs with boundary violations or factual warnings are retained in the raw files and should not be counted as clean isolation of that treatment.",
        "",
        "The diagnostic columns in `experiment-3-results.csv` describe text changes. The existing Gemini judge gave 5/5 on every dimension for all 30 imported answers, so that judge cannot establish which treatment improved teaching. No human comprehension outcomes exist.",
        "",
        "## Files",
        "",
        "`experiment-3-results.csv` has one row per saved variant. Each `transform-*.json` includes the full rewrite, per-treatment diff, pipeline stages, and fidelity warnings. Source and variant IDs connect these files to the app database.",
        "",
    ]
    (OUT / "experiment-3-report.md").write_text("\n".join(lines), encoding="utf-8")
    return rows


def build_stage4(conn: sqlite3.Connection, treatment: str) -> list[dict]:
    rows = []
    for topic in TOPICS:
        for author in ("chatgpt", "claude"):
            baseline = details(conn, source_id(conn, topic, author))
            bw, bs, bc = short_metrics(baseline)
            files = (
                ("gemini-3.5-flash-lite", OUT / f"transform-{topic}-{author}-{treatment}.json"),
                ("gemini-3.1-flash-lite", OUT / f"cross-{topic}-{author}-{treatment}-gemini-3.1-flash-lite.json"),
            )
            for rewriter, path in files:
                if not path.exists():
                    continue
                raw = load(path)
                variant = details(conn, raw["variant_response_id"])
                vw, vs, vc = short_metrics(variant)
                warnings = (raw.get("fidelity") or {}).get("warnings") or []
                rows.append({
                    "topic": topic,
                    "source_author": author,
                    "source_model": baseline["model_id"],
                    "rewriter_model": rewriter,
                    "treatment": treatment,
                    "source_response_id": baseline["id"],
                    "variant_response_id": variant["id"],
                    "fidelity_verdict": raw["fidelity"]["verdict"],
                    "warning_types": ";".join(w.get("type", "") for w in warnings),
                    "source_words": bw,
                    "variant_words": vw,
                    "word_delta": vw - bw,
                    "source_avg_sentence_words": bs,
                    "variant_avg_sentence_words": vs,
                    "source_lexical_checklist_matches": bc,
                    "variant_lexical_checklist_matches": vc,
                    "app_estimated_cost_usd": raw.get("total_cost_usd", 0),
                    "raw_file": path.name,
                })
    write_csv(OUT / "experiment-4-results.csv", rows)
    by_rewriter = defaultdict(list)
    for row in rows:
        by_rewriter[row["rewriter_model"]].append(row)
    lines = [
        "# Experiment 4 - Cross-model transformations",
        "",
        f"Treatment: **{treatment}**. There are **{len(rows)}/20** saved cells: ChatGPT and Claude source answers, each rewritten by two Gemini models across five questions.",
        "",
        "| Rewriter | Cells | Clean | Warnings | Serious concerns | Median word change |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rewriter in ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite"):
        group = by_rewriter[rewriter]
        counts = Counter(row["fidelity_verdict"] for row in group)
        median = statistics.median([row["word_delta"] for row in group]) if group else 0
        lines.append(f"| {rewriter} | {len(group)} | {counts['clean']} | {counts['warnings']} | {counts['serious_concerns']} | {median:+g} |")
    lines += [
        "",
        "## Interpretation limits",
        "",
        "Both rewriters use Gemini. This is a comparison of rewriter models on ChatGPT and Claude source text; it does **not** fill the ChatGPT-to-Claude or Claude-to-ChatGPT website rewrite cells in the manual. Neither source model has an API key configured in this app.",
        "",
        "Any change can reflect the treatment, the rewriter, a second pass, or their interaction. The all-5/5 Gemini judge cannot rank these outputs, and no human comprehension outcome was collected. The CSV supports matched descriptive comparisons and fidelity screening, not a causal portability claim.",
        "",
        "The app has no catalogue price for `gemini-3.1-flash-lite`; its zero cost estimate in raw results means **unestimated**, not free.",
        "",
    ]
    (OUT / "experiment-4-report.md").write_text("\n".join(lines), encoding="utf-8")
    return rows


def build_stage5(conn: sqlite3.Connection) -> list[dict]:
    rows = []
    lines = [
        "# Experiment 5 - AI proxy answerability",
        "",
        "This is the manual workflow's AI proxy, not the platform's human comprehension experiment. Studies were left in Draft and have no participant submissions.",
        "",
        "| Topic | No-text correct | Diagnostic items | Condition | Correct with exact quote | Diagnostic correct with quote |",
        "| --- | ---: | ---: | --- | ---: | ---: |",
    ]
    for topic in TOPICS:
        path = OUT / f"proxy-{topic}.json"
        if not path.exists():
            continue
        result = load(path)
        for condition in result["conditions"]:
            response = details(conn, condition["response_id"])
            if response["parent_response_id"]:
                parent = details(conn, response["parent_response_id"])
                author = "chatgpt" if parent["provider"] == "openai" else "claude"
                label = f"{author} transformed"
            else:
                author = "chatgpt" if response["provider"] == "openai" else "claude"
                label = f"{author} baseline"
            row = {
                "topic": topic,
                "condition": label,
                "response_id": response["id"],
                "study_id": result["study_id"],
                "item_count": result["item_count"],
                "no_explanation_correct": result["baseline_correct_count"],
                "diagnostic_item_count": result["diagnostic_item_count"],
                "correct_with_quote": condition["grounded_correct"],
                "diagnostic_correct_with_quote": condition["diagnostic_grounded_correct"],
                "proxy_model": result["model_id"],
                "raw_file": path.name,
            }
            rows.append(row)
            lines.append(f"| {topic} | {row['no_explanation_correct']}/{row['item_count']} | {row['diagnostic_item_count']} | {label} | {row['correct_with_quote']}/{row['item_count']} | {row['diagnostic_correct_with_quote']}/{row['diagnostic_item_count']} |")
    write_csv(OUT / "experiment-5-results.csv", rows)
    lines += [
        "",
        "## Interpretation",
        "",
        "First read the no-explanation result. When diagnostic items = 0, Gemini already answered every question before seeing an explanation, so the study cannot measure added answerability. A correct choice plus an exact quote shows textual support only. It does not show that a person learned the concept.",
        "",
        "Question wording and randomized answer order are stored in each `study-*-config.json`. Per-item choices and quotes are stored in each `proxy-*.json`. The corresponding `proxy-*-report.md` is the report persisted by the app.",
        "",
    ]
    (OUT / "experiment-5-report.md").write_text("\n".join(lines), encoding="utf-8")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("treatment", choices=[f"T{i}" for i in range(1, 7)])
    treatment = parser.parse_args().treatment
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    questions = []
    for row in conn.execute("SELECT id, text, domain, topic, conceptual_difficulty, factual_checklist FROM research_questions"):
        if row["topic"].strip() in TOPICS and row["text"].startswith((
            "How do write-through", "How does a B-tree", "How does the TCP",
            "How does a vaccine", "How is compound interest",
        )):
            item = dict(row)
            item["topic"] = item["topic"].strip()
            item["factual_checklist"] = json.loads(item["factual_checklist"])
            questions.append(item)
    question_ids = {q["id"] for q in questions}
    answers = []
    for row in conn.execute("""
        SELECT id, question_id, provider, model_id, label, text, created_at,
               control_limitations, is_synthetic
        FROM responses WHERE origin='manual_import' ORDER BY question_id, provider, label
    """):
        if row["question_id"] not in question_ids:
            continue
        item = dict(row)
        item["control_limitations"] = json.loads(item["control_limitations"])
        answers.append(item)
    (OUT / "input-dataset.json").write_text(json.dumps({
        "questions": questions,
        "imported_answers": answers,
        "note": "Web-chat answers are copied from the app database. Hidden provider settings are unknown.",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    stage3 = build_stage3(conn)
    stage4 = build_stage4(conn, treatment)
    stage5 = build_stage5(conn)
    (OUT / "README.md").write_text("\n".join([
        "# ExplanationLab research results - 2026-10-26",
        "",
        "These are saved results for the manual Gemini-key workflow. Open the three experiment reports first.",
        "",
        f"- Experiment 3: {len(stage3)}/60 single-treatment runs; see `experiment-3-report.md`, `experiment-3-results.csv`, and `transform-*.json`.",
        f"- Experiment 4: {len(stage4)}/20 rewriter cells for {treatment}; see `experiment-4-report.md`, `experiment-4-results.csv`, and `cross-*.json`.",
        f"- Experiment 5: {len(stage5)}/20 proxy condition results; see `experiment-5-report.md`, `experiment-5-results.csv`, `proxy-*.json`, and `study-*-config.json`.",
        f"- Inputs: `input-dataset.json` preserves {len(questions)} questions and {len(answers)} imported answers so the result folder can be read without opening the app.",
        "",
        "The app database retains the source answers, saved variants, fidelity audits, and draft studies. CSV files link rows to response and study IDs. No real participant was tested. The ChatGPT/Claude website rewrite cells in Experiment 4 require access to those sites or provider keys and are not represented by the Gemini rewriter comparison here.",
        "",
    ]), encoding="utf-8")
    print("reports built", len(stage3), len(stage4), len(stage5))


if __name__ == "__main__":
    main()
