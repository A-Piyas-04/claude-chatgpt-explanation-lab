"""Emit the shared contract into packages/shared-schemas.

Run after changing an enum, a treatment, or the model catalogue:

    python -m explanationlab.export_schemas

Generating rather than hand-writing the TypeScript means the frontend's notion
of "what treatments exist" cannot drift from the backend's. The generated files
are committed so a `npm install` alone is enough to build the web app.
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import REPO_ROOT
from .enums import (
    EvalDimension,
    EvidenceClass,
    ExperimentStatus,
    ExperimentType,
    GradingMode,
    ItemFormat,
    LearnerLevel,
    Provider,
    PromptCondition,
    ResponseKind,
    ResponseOrigin,
    RunStatus,
    StudyStatus,
    Treatment,
)
from .evaluation.rubrics import JUDGE_DIMENSIONS, JUDGE_RUBRIC_VERSION
from .prompts.builtin import BUILTIN_PROMPTS
from .providers.catalog import PRICING_VERIFIED_ON, seed_rows
from .transformations.strategies import ALL_STRATEGIES

OUT_DIR = REPO_ROOT / "packages" / "shared-schemas"

# A second copy lands inside the web app's own source tree. Next.js resolves
# modules under its project root without extra configuration, and a generated
# copy is cheaper to maintain than a monorepo build step for one file.
WEB_OUT_DIR = REPO_ROOT / "apps" / "web" / "lib" / "generated"

ENUMS = {
    "Provider": Provider,
    "ExperimentType": ExperimentType,
    "ExperimentStatus": ExperimentStatus,
    "ResponseKind": ResponseKind,
    "ResponseOrigin": ResponseOrigin,
    "LearnerLevel": LearnerLevel,
    "PromptCondition": PromptCondition,
    "Treatment": Treatment,
    "RunStatus": RunStatus,
    "ItemFormat": ItemFormat,
    "EvalDimension": EvalDimension,
    "GradingMode": GradingMode,
    "StudyStatus": StudyStatus,
    "EvidenceClass": EvidenceClass,
}


def build_catalog() -> dict:
    return {
        "_generated_by": "python -m explanationlab.export_schemas",
        "_warning": "Generated file. Edit the Python source, then regenerate.",
        "enums": {name: [member.value for member in enum] for name, enum in ENUMS.items()},
        "treatments": [
            {
                "key": s.key,
                "name": s.name,
                "category": s.category,
                "description": s.description,
                "boundary_note": s.boundary_note,
                "default_params": s.default_params,
                "version": s.version,
            }
            for s in ALL_STRATEGIES
        ],
        "prompt_conditions": [
            {
                "key": p["key"],
                "name": p["name"],
                "condition": p["condition"],
                "description": p["description"],
            }
            for p in BUILTIN_PROMPTS
        ],
        "judge_rubric": {
            "version": JUDGE_RUBRIC_VERSION,
            "dimensions": [
                {"metric": d["metric"], "question": d["question"], "anchors": d["anchors"]}
                for d in JUDGE_DIMENSIONS
            ],
        },
        "model_catalog_seed": {
            "pricing_verified_on": PRICING_VERIFIED_ON,
            "models": [
                {
                    "provider": row["provider"],
                    "model_id": row["model_id"],
                    "display_name": row["display_name"],
                    "tier": row["tier"],
                    "input_cost_per_mtok": row["input_cost_per_mtok"],
                    "output_cost_per_mtok": row["output_cost_per_mtok"],
                    "supports_temperature": row["supports_temperature"],
                    "supports_effort": row["supports_effort"],
                    "default_effort": row["default_effort"],
                    "notes": row["notes"],
                }
                for row in seed_rows()
            ],
        },
        "evidence_class_meaning": {
            EvidenceClass.AUTOMATED_DIAGNOSTIC.value:
                "Deterministic surface measure. Describes a text; does not measure understanding.",
            EvidenceClass.AI_JUDGE_OPINION.value:
                "A judge model's rating. Subject to known biases; not comprehension evidence.",
            EvidenceClass.HUMAN_PREFERENCE.value:
                "Participant self-report. Perceived ease can diverge from actual understanding.",
            EvidenceClass.HUMAN_COMPREHENSION.value:
                "Measured learner performance. The primary evidence in this platform.",
        },
    }


def ts_union(name: str, values: list[str]) -> str:
    members = " | ".join(f'"{v}"' for v in values)
    return f"export type {name} = {members};"


def build_types(catalog: dict) -> str:
    lines = [
        "/**",
        " * GENERATED FILE — do not edit.",
        " *",
        " * Produced by `python -m explanationlab.export_schemas` from the backend",
        " * enums and strategy definitions, so the two cannot drift apart.",
        " */",
        "",
        "import catalog from \"./catalog.json\";",
        "",
        "export { catalog };",
        "",
    ]
    for name, values in catalog["enums"].items():
        lines.append(ts_union(name, values))
    lines += [
        "",
        "export interface TreatmentDefinition {",
        "  key: Treatment;",
        "  name: string;",
        "  category: string;",
        "  description: string;",
        "  /** What this treatment must NOT do. Checked in pipeline stage D. */",
        "  boundary_note: string;",
        "  default_params: Record<string, unknown>;",
        "  version: number;",
        "}",
        "",
        "export const TREATMENTS = catalog.treatments as TreatmentDefinition[];",
        "",
        "export const EVIDENCE_CLASS_MEANING = catalog.evidence_class_meaning as Record<",
        "  EvidenceClass,",
        "  string",
        ">;",
        "",
        "/** Canonical composition order when several treatments are combined. */",
        "export const TREATMENT_ORDER: Treatment[] = [",
        '  "T3",',
        '  "T4",',
        '  "T6",',
        '  "T1",',
        '  "T2",',
        '  "T5",',
        "];",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    catalog = build_catalog()
    payload = json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"
    types = build_types(catalog)

    for directory in (OUT_DIR, WEB_OUT_DIR):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "catalog.json").write_text(payload, encoding="utf-8")
        (directory / "index.ts").write_text(types, encoding="utf-8")
        print(f"Wrote {directory / 'catalog.json'}")
        print(f"Wrote {directory / 'index.ts'}")


if __name__ == "__main__":
    main()
