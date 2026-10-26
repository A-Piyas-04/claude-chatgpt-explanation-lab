"""Apply one treatment with a second Gemini model to both source authors.

The first Gemini-model cells come from run_stage3.py. These runs provide a
second rewriter model, but do not substitute for ChatGPT/Claude web rewrites.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
API = "http://localhost:3000/api/proxy"
MODEL = "gemini-3.1-flash-lite"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("treatment", choices=[f"T{i}" for i in range(1, 7)])
    treatment = parser.parse_args().treatment
    conn = sqlite3.connect(ROOT / "apps/api/explanationlab.sqlite3")
    conn.row_factory = sqlite3.Row
    sources = list(conn.execute("""
        SELECT r.id, r.provider, q.topic
        FROM responses r JOIN research_questions q ON q.id = r.question_id
        WHERE r.origin = 'manual_import' AND r.is_synthetic = 0
          AND lower(r.label) LIKE '%base%'
        ORDER BY q.topic, r.provider
    """))
    assert len(sources) == 10, f"Expected 10 baselines, found {len(sources)}"
    last_start = 0.0
    for source in sources:
        topic = source["topic"].strip()
        author = "chatgpt" if source["provider"] == "openai" else "claude"
        path = OUT / f"cross-{topic}-{author}-{treatment}-{MODEL}.json"
        if path.exists():
            print(topic, author, "already saved", flush=True)
            continue
        remaining = 22.0 - (time.monotonic() - last_start)
        if remaining > 0:
            time.sleep(remaining)
        last_start = time.monotonic()
        payload = {
            "treatments": [treatment],
            "provider": "gemini",
            "model_id": MODEL,
            "run_analysis": True,
            "run_planning": True,
            "run_fidelity": True,
            "save_variant": True,
        }
        request = urllib.request.Request(
            API + f"/responses/{source['id']}/transform",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        for attempt in range(1, 4):
            try:
                with urllib.request.urlopen(request, timeout=240) as response:
                    result = json.load(response)
                assert result.get("variant_response_id")
                path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                print(topic, author, treatment, (result.get("fidelity") or {}).get("verdict"), result["variant_response_id"], flush=True)
                break
            except (urllib.error.URLError, TimeoutError, AssertionError) as exc:
                if attempt == 3:
                    print(topic, author, "FAILED", str(exc), flush=True)
                    raise
                print(topic, author, "retrying after", str(exc), flush=True)
                time.sleep(65)


if __name__ == "__main__":
    main()
