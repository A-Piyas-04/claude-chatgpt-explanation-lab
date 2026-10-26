"""Create five draft studies and run Gemini's AI answerability proxy.

The proxy is not a human comprehension experiment. It checks answerability and
records the no-explanation control for the same multiple-choice items.
"""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
API = "http://localhost:3000/api/proxy"
MODEL = "gemini-3.5-flash-lite"


def call(method: str, path: str, payload: dict | None = None) -> dict:
    request = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"} if payload is not None else {},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=240) as response:
        return json.load(response)


def shuffled_items(topic: str, items: list[dict], topic_index: int) -> list[dict]:
    rng = random.Random(20261026 + topic_index)
    prepared = []
    for item in items:
        order = list(range(len(item["options"])))
        rng.shuffle(order)
        prepared.append({
            "format": "multiple_choice",
            "dimension": item["dimension"],
            "prompt": item["prompt"],
            "options": [item["options"][i] for i in order],
            "correct_option_index": order.index(item["correct_option_index"]),
            "misconception_option_indexes": [],
            "max_score": 1,
            "is_required": True,
        })
    return prepared


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("treatment", choices=[f"T{i}" for i in range(1, 7)])
    treatment = parser.parse_args().treatment
    conn = sqlite3.connect(ROOT / "apps/api/explanationlab.sqlite3")
    conn.row_factory = sqlite3.Row
    bank = json.loads((OUT / "study-items.json").read_text(encoding="utf-8"))
    for index, topic in enumerate(("caching", "databases", "tcp", "immunology", "interest")):
        bases = list(conn.execute("""
            SELECT r.id, r.provider, q.id AS question_id
            FROM responses r JOIN research_questions q ON q.id = r.question_id
            WHERE trim(q.topic, ' ' || char(9)) = ? AND r.origin = 'manual_import'
              AND lower(r.label) LIKE '%base%' AND r.is_synthetic = 0
            ORDER BY r.provider DESC
        """, (topic,)))
        assert len(bases) == 2, (topic, "needs two baselines")
        by_author = {"chatgpt" if row["provider"] == "openai" else "claude": row for row in bases}
        variants = {}
        for author in ("chatgpt", "claude"):
            path = OUT / f"transform-{topic}-{author}-{treatment}.json"
            result = json.loads(path.read_text(encoding="utf-8"))
            if result["fidelity"]["verdict"] == "clean":
                variants[author] = result["variant_response_id"]
            else:
                print(topic, author, "excluded from study:", result["fidelity"]["verdict"], flush=True)
        assert variants, (topic, "no clean transformed variant")
        config_path = OUT / f"study-{topic}-config.json"
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding="utf-8"))
        else:
            config = {
                "name": f"AI proxy - {topic} - baselines vs {treatment}",
                "question_id": by_author["chatgpt"]["question_id"],
                "response_ids": [
                    by_author["chatgpt"]["id"],
                    by_author["claude"]["id"],
                    *[variants[author] for author in ("chatgpt", "claude") if author in variants],
                ],
                "items": shuffled_items(topic, bank[topic], index),
                "seed": 20261026 + index,
                "balance_conditions": True,
            }
            config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        study_path = OUT / f"study-{topic}.json"
        if study_path.exists():
            study_id = json.loads(study_path.read_text(encoding="utf-8"))["id"]
        else:
            study = call("POST", "/studies", config)
            study_id = study["id"]
            study_path.write_text(json.dumps({"id": study_id, "name": study["name"], "status": study["status"]}, indent=2), encoding="utf-8")
        proxy_path = OUT / f"proxy-{topic}.json"
        if proxy_path.exists():
            print(topic, "already evaluated", flush=True)
            continue
        for attempt in range(1, 4):
            try:
                result = call("POST", f"/studies/{study_id}/proxy-evaluation", {"provider": "gemini", "model_id": MODEL})
                proxy_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                report = call("GET", f"/reports/{result['id']}")
                (OUT / f"proxy-{topic}-report.md").write_text(report["body_markdown"], encoding="utf-8")
                print(topic, "evaluated", result["diagnostic_item_count"], "diagnostic items", flush=True)
                break
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == 3:
                    print(topic, "FAILED", str(exc), flush=True)
                    raise
                print(topic, "retrying after", str(exc), flush=True)
                time.sleep(65)
        time.sleep(24)


if __name__ == "__main__":
    main()
