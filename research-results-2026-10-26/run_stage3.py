"""Run the manual-workflow single-treatment comparison on stored baselines.

This script is resumable: a completed raw JSON file is not regenerated.
"""

from __future__ import annotations

import json
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
DB = ROOT / "apps/api/explanationlab.sqlite3"
API = "http://localhost:3000/api/proxy"
MODEL = "gemini-3.5-flash-lite"


def post(path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=240) as response:
        return json.load(response)


def main() -> None:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    sources = list(
        conn.execute(
            """
            SELECT r.id, r.provider, r.label, q.topic, q.text AS question
            FROM responses r JOIN research_questions q ON q.id = r.question_id
            WHERE r.origin = 'manual_import' AND r.is_synthetic = 0
              AND lower(r.label) LIKE '%base%'
            ORDER BY q.topic, r.provider
            """
        )
    )
    assert len(sources) == 10, f"Expected 10 baseline sources; found {len(sources)}"
    for source in sources:
        topic = source["topic"].strip()
        author = "chatgpt" if source["provider"] == "openai" else "claude"
        for treatment in ("T1", "T2", "T3", "T4", "T5", "T6"):
            path = OUT / f"transform-{topic}-{author}-{treatment}.json"
            if path.exists():
                print(topic, author, treatment, "already saved", flush=True)
                continue
            payload = {
                "treatments": [treatment],
                "provider": "gemini",
                "model_id": MODEL,
                "run_analysis": True,
                "run_planning": True,
                "run_fidelity": True,
                "save_variant": True,
            }
            for attempt in range(1, 4):
                try:
                    result = post(f"/responses/{source['id']}/transform", payload)
                    assert result.get("variant_response_id"), "Variant was not saved"
                    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                    verdict = (result.get("fidelity") or {}).get("verdict")
                    print(topic, author, treatment, "saved", verdict, result["variant_response_id"], flush=True)
                    break
                except (urllib.error.URLError, TimeoutError, AssertionError) as exc:
                    if attempt == 3:
                        print(topic, author, treatment, "FAILED", str(exc), flush=True)
                        raise
                    time.sleep(3 * attempt)


if __name__ == "__main__":
    main()
