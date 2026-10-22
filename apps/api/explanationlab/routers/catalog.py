"""Research library: questions, learner profiles, models, prompts, strategies."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..enums import Provider
from ..models import (
    GradingRubric,
    LearnerProfile,
    ModelCatalogEntry,
    PromptTemplate,
    ResearchQuestion,
    TransformationStrategy,
    utcnow,
)
from ..prompts import registry as prompt_registry
from ..providers.base import ProviderError
from ..providers.catalog import UNKNOWN_MODEL_NOTE, find_seed
from ..providers.registry import get_provider, provider_configured
from ..schemas import (
    LearnerProfileCreate,
    LearnerProfileOut,
    ModelCatalogOut,
    ModelCatalogUpdate,
    PromptTemplateCreate,
    PromptTemplateOut,
    PromptVersionCreate,
    QuestionCreate,
    QuestionOut,
    QuestionUpdate,
)
from ..security import require_researcher

router = APIRouter(dependencies=[Depends(require_researcher)])


# ---------------------------------------------------------------------------
# Research questions
# ---------------------------------------------------------------------------


@router.get("/questions", response_model=list[QuestionOut], tags=["questions"])
def list_questions(
    db: Session = Depends(get_db),
    domain: str | None = None,
    search: str | None = None,
    limit: int = Query(default=200, le=500),
) -> list[ResearchQuestion]:
    stmt = select(ResearchQuestion).order_by(ResearchQuestion.created_at.desc()).limit(limit)
    if domain:
        stmt = stmt.where(ResearchQuestion.domain == domain)
    if search:
        stmt = stmt.where(ResearchQuestion.text.ilike(f"%{search}%"))
    return list(db.execute(stmt).scalars())


@router.post("/questions", response_model=QuestionOut, status_code=201, tags=["questions"])
def create_question(payload: QuestionCreate, db: Session = Depends(get_db)) -> ResearchQuestion:
    question = ResearchQuestion(**payload.model_dump())
    db.add(question)
    db.commit()
    return question


@router.get("/questions/{question_id}", response_model=QuestionOut, tags=["questions"])
def get_question(question_id: str, db: Session = Depends(get_db)) -> ResearchQuestion:
    question = db.get(ResearchQuestion, question_id)
    if question is None:
        raise HTTPException(404, "Research question not found.")
    return question


@router.patch("/questions/{question_id}", response_model=QuestionOut, tags=["questions"])
def update_question(
    question_id: str, payload: QuestionUpdate, db: Session = Depends(get_db)
) -> ResearchQuestion:
    question = db.get(ResearchQuestion, question_id)
    if question is None:
        raise HTTPException(404, "Research question not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(question, field, value)
    db.commit()
    return question


@router.post("/questions/{question_id}/duplicate", response_model=QuestionOut, tags=["questions"])
def duplicate_question(question_id: str, db: Session = Depends(get_db)) -> ResearchQuestion:
    source = db.get(ResearchQuestion, question_id)
    if source is None:
        raise HTTPException(404, "Research question not found.")
    copy = ResearchQuestion(
        text=f"{source.text} (copy)",
        domain=source.domain,
        topic=source.topic,
        conceptual_difficulty=source.conceptual_difficulty,
        factual_checklist=list(source.factual_checklist or []),
        checklist_reviewed_by=source.checklist_reviewed_by,
        notes=source.notes,
    )
    db.add(copy)
    db.commit()
    return copy


@router.delete("/questions/{question_id}", status_code=204, tags=["questions"])
def delete_question(question_id: str, db: Session = Depends(get_db)) -> None:
    question = db.get(ResearchQuestion, question_id)
    if question is None:
        raise HTTPException(404, "Research question not found.")
    db.delete(question)
    db.commit()


@router.get("/domains", tags=["questions"])
def list_domains(db: Session = Depends(get_db)) -> list[str]:
    return sorted(
        {d for d in db.execute(select(ResearchQuestion.domain)).scalars() if d}
    )


# ---------------------------------------------------------------------------
# Learner profiles
# ---------------------------------------------------------------------------


@router.get("/learner-profiles", response_model=list[LearnerProfileOut], tags=["profiles"])
def list_profiles(db: Session = Depends(get_db)) -> list[LearnerProfile]:
    return list(db.execute(select(LearnerProfile).order_by(LearnerProfile.name)).scalars())


@router.post(
    "/learner-profiles", response_model=LearnerProfileOut, status_code=201, tags=["profiles"]
)
def create_profile(
    payload: LearnerProfileCreate, db: Session = Depends(get_db)
) -> LearnerProfile:
    existing = db.execute(
        select(LearnerProfile).where(LearnerProfile.name == payload.name)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(409, "A learner profile with that name already exists.")
    profile = LearnerProfile(
        name=payload.name,
        level=payload.level.value,
        description=payload.description,
        assumed_prior_knowledge=payload.assumed_prior_knowledge,
        unfamiliar_with=payload.unfamiliar_with,
    )
    db.add(profile)
    db.commit()
    return profile


# ---------------------------------------------------------------------------
# Model catalogue
# ---------------------------------------------------------------------------


@router.get("/models", response_model=list[ModelCatalogOut], tags=["models"])
def list_models(
    db: Session = Depends(get_db), enabled_only: bool = False
) -> list[ModelCatalogEntry]:
    stmt = select(ModelCatalogEntry).order_by(
        ModelCatalogEntry.provider, ModelCatalogEntry.model_id
    )
    if enabled_only:
        stmt = stmt.where(ModelCatalogEntry.is_enabled.is_(True))
    return list(db.execute(stmt).scalars())


@router.patch("/models/{entry_id}", response_model=ModelCatalogOut, tags=["models"])
def update_model(
    entry_id: str, payload: ModelCatalogUpdate, db: Session = Depends(get_db)
) -> ModelCatalogEntry:
    entry = db.get(ModelCatalogEntry, entry_id)
    if entry is None:
        raise HTTPException(404, "Model catalogue entry not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    return entry


@router.post("/models/refresh", tags=["models"])
def refresh_models(db: Session = Depends(get_db)) -> dict:
    """Reconcile the catalogue against each provider's live model list.

    Model IDs go stale. Rather than trusting a hardcoded list forever, this asks
    the provider what exists, marks what it confirms, and flags anything in the
    catalogue the provider no longer lists — instead of discovering it as a
    mid-batch 404.
    """
    report: dict = {"providers": {}, "discovered": [], "unverified": []}

    for provider in (Provider.OPENAI.value, Provider.ANTHROPIC.value, Provider.GEMINI.value):
        if not provider_configured(provider):
            report["providers"][provider] = {
                "status": "skipped",
                "reason": "no API key configured",
            }
            continue
        try:
            live_ids = set(get_provider(provider, allow_demo=False).list_models())
        except ProviderError as exc:
            report["providers"][provider] = {"status": "error", "reason": str(exc)}
            continue

        entries = list(
            db.execute(
                select(ModelCatalogEntry).where(ModelCatalogEntry.provider == provider)
            ).scalars()
        )
        known = {e.model_id for e in entries}

        for entry in entries:
            entry.verified_live = entry.model_id in live_ids
            entry.last_verified_at = utcnow()
            if not entry.verified_live:
                report["unverified"].append(f"{provider}/{entry.model_id}")

        for model_id in sorted(live_ids - known):
            seed = find_seed(provider, model_id)
            db.add(
                ModelCatalogEntry(
                    provider=provider,
                    model_id=model_id,
                    display_name=model_id,
                    tier="unknown",
                    input_cost_per_mtok=seed.input_cost_per_mtok if seed else None,
                    output_cost_per_mtok=seed.output_cost_per_mtok if seed else None,
                    # Conservative defaults: never send a parameter that might 400.
                    supports_temperature=False,
                    supports_effort=True,
                    supports_structured_output=True,
                    is_enabled=False,
                    verified_live=True,
                    last_verified_at=utcnow(),
                    notes=UNKNOWN_MODEL_NOTE,
                )
            )
            report["discovered"].append(f"{provider}/{model_id}")

        report["providers"][provider] = {
            "status": "ok",
            "live_model_count": len(live_ids),
        }

    db.commit()
    report["note"] = (
        "Newly discovered models are added disabled, with no pricing and conservative "
        "capability flags. Review and enable them before use. Entries marked unverified "
        "were not in the provider's live list."
    )
    return report


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------


@router.get("/prompts", response_model=list[PromptTemplateOut], tags=["prompts"])
def list_prompts(db: Session = Depends(get_db)) -> list[PromptTemplate]:
    return list(db.execute(select(PromptTemplate).order_by(PromptTemplate.key)).scalars())


@router.post("/prompts", response_model=PromptTemplateOut, status_code=201, tags=["prompts"])
def create_prompt(
    payload: PromptTemplateCreate, db: Session = Depends(get_db)
) -> PromptTemplate:
    if prompt_registry.get_template(db, payload.key) is not None:
        raise HTTPException(409, f"A prompt template with key '{payload.key}' already exists.")
    template = PromptTemplate(
        key=payload.key,
        name=payload.name,
        condition=payload.condition,
        description=payload.description,
        is_builtin=False,
    )
    db.add(template)
    db.flush()
    prompt_registry.add_version(
        db,
        template,
        system_text=payload.system_text,
        user_template=payload.user_template,
        changelog="Initial version.",
    )
    db.commit()
    return template


@router.get("/prompts/{key}", response_model=PromptTemplateOut, tags=["prompts"])
def get_prompt(key: str, db: Session = Depends(get_db)) -> PromptTemplate:
    template = prompt_registry.get_template(db, key)
    if template is None:
        raise HTTPException(404, "Prompt template not found.")
    return template


@router.post(
    "/prompts/{key}/versions", response_model=PromptTemplateOut, status_code=201, tags=["prompts"]
)
def add_prompt_version(
    key: str, payload: PromptVersionCreate, db: Session = Depends(get_db)
) -> PromptTemplate:
    """Append a version. Earlier versions are immutable.

    Experiments reference a specific version id and snapshot the rendered text,
    so editing a template never alters a completed experiment's record.
    """
    template = prompt_registry.get_template(db, key)
    if template is None:
        raise HTTPException(404, "Prompt template not found.")
    prompt_registry.add_version(
        db,
        template,
        system_text=payload.system_text,
        user_template=payload.user_template,
        changelog=payload.changelog,
    )
    db.commit()
    db.refresh(template)
    return template


# ---------------------------------------------------------------------------
# Transformation strategies and rubrics
# ---------------------------------------------------------------------------


@router.get("/transformations/strategies", tags=["transformations"])
def list_strategies(db: Session = Depends(get_db)) -> list[dict]:
    strategies = list(
        db.execute(
            select(TransformationStrategy).order_by(TransformationStrategy.key)
        ).scalars()
    )
    return [
        {
            "id": s.id,
            "key": s.key,
            "name": s.name,
            "description": s.description,
            "category": s.category,
            "boundary_note": s.boundary_note,
            "versions": [
                {
                    "id": v.id,
                    "version": v.version,
                    "is_active": v.is_active,
                    "default_params": v.default_params,
                    "instruction_template": v.instruction_template,
                }
                for v in s.versions
            ],
        }
        for s in strategies
    ]


@router.get("/rubrics", tags=["evaluation"])
def list_rubrics(db: Session = Depends(get_db)) -> list[dict]:
    from ..evaluation.rubrics import JUDGE_DIMENSIONS, JUDGE_RUBRIC_VERSION

    stored = list(db.execute(select(GradingRubric).order_by(GradingRubric.key)).scalars())
    return [
        {
            "key": "explanation_quality",
            "version": JUDGE_RUBRIC_VERSION,
            "name": "AI judge — explanation quality",
            "kind": "judge",
            "criteria": JUDGE_DIMENSIONS,
            "max_score": 5,
        },
        *[
            {
                "key": r.key,
                "version": r.version,
                "name": r.name,
                "kind": "short_answer",
                "criteria": r.criteria,
                "max_score": r.max_score,
            }
            for r in stored
        ],
    ]
