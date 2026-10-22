"""The single doorway through which every model call passes.

Responsibilities concentrated here so no caller can bypass them:

- cost estimation and the daily spend cap
- the deterministic response cache (and honest reporting of cache reuse)
- token/cost/latency/error accounting into ``usage_records``
- structured-output parsing with one repair retry
- propagating synthetic provenance

Keeping this in one place is what makes "review API costs, errors and
generation metadata" (acceptance criterion 16) answerable from the database
rather than from logs.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .enums import CallPurpose
from .models import ModelCatalogEntry, ResponseCache, UsageRecord, utcnow
from .providers.base import GenerationRequest, GenerationResult, ProviderError
from .providers.catalog import estimate_cost_usd
from .providers.registry import get_provider

log = logging.getLogger(__name__)


class SpendCapExceeded(ProviderError):
    def __init__(self, spent: float, cap: float):
        super().__init__(
            f"Daily spend cap reached: ${spent:.4f} of ${cap:.2f} estimated. "
            "Raise DAILY_SPEND_CAP_USD in .env to continue.",
            error_type="spend_cap_exceeded",
        )


class StructuredOutputError(ProviderError):
    pass


@dataclass(slots=True)
class CallOutcome:
    result: GenerationResult
    cost_usd: float
    usage_record_id: str | None


def spend_today(db: Session) -> float:
    """Estimated non-synthetic spend since midnight UTC."""
    start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total = db.execute(
        select(func.coalesce(func.sum(UsageRecord.cost_usd), 0.0)).where(
            UsageRecord.created_at >= start,
            UsageRecord.is_synthetic.is_(False),
        )
    ).scalar_one()
    return float(total or 0.0)


def catalog_entry(db: Session, provider: str, model_id: str) -> ModelCatalogEntry | None:
    return db.execute(
        select(ModelCatalogEntry).where(
            ModelCatalogEntry.provider == provider,
            ModelCatalogEntry.model_id == model_id,
        )
    ).scalar_one_or_none()


def call_model(
    db: Session,
    *,
    provider: str,
    model_id: str,
    request: GenerationRequest,
    purpose: CallPurpose,
    experiment_id: str | None = None,
    use_cache: bool | None = None,
) -> CallOutcome:
    """Execute one model call with full accounting.

    Raises :class:`ProviderError` subclasses on failure; the caller decides
    whether that fails a single run or the whole batch.
    """
    settings = get_settings()
    entry = catalog_entry(db, provider, model_id)
    if entry is not None and not entry.is_enabled:
        raise ProviderError(
            f"Model '{model_id}' is disabled in the catalogue.", error_type="model_disabled"
        )

    adapter = get_provider(provider)
    is_demo = getattr(adapter, "emulating", None) is not None

    if not is_demo:
        spent = spend_today(db)
        if spent >= settings.daily_spend_cap_usd:
            raise SpendCapExceeded(spent, settings.daily_spend_cap_usd)

    cache_enabled = settings.enable_response_cache if use_cache is None else use_cache
    request_hash = request.cache_key(provider, model_id)
    cacheable = cache_enabled and request.is_deterministic

    # --- cache hit -------------------------------------------------------
    if cacheable:
        cached = db.get(ResponseCache, request_hash)
        if cached is not None:
            cached.hit_count += 1
            db.flush()
            result = GenerationResult(
                text=cached.text,
                provider=provider,
                model_id=model_id,
                input_tokens=cached.input_tokens,
                output_tokens=cached.output_tokens,
                latency_ms=0,
                finish_reason=cached.finish_reason,
                control_limitations=["Served from the local response cache; no API call was made."],
                effective_settings={},
                served_from_cache=True,
                is_synthetic=is_demo,
            )
            usage = UsageRecord(
                provider=provider,
                model_id=model_id,
                purpose=purpose.value,
                input_tokens=cached.input_tokens or 0,
                output_tokens=cached.output_tokens or 0,
                cost_usd=0.0,  # a cache hit costs nothing
                latency_ms=0,
                success=True,
                served_from_cache=True,
                experiment_id=experiment_id,
                is_synthetic=is_demo,
            )
            db.add(usage)
            db.flush()
            return CallOutcome(result=result, cost_usd=0.0, usage_record_id=usage.id)

    # --- live call -------------------------------------------------------
    try:
        result = adapter.generate(model_id, request)
    except ProviderError as exc:
        db.add(
            UsageRecord(
                provider=provider,
                model_id=model_id,
                purpose=purpose.value,
                success=False,
                error_type=exc.error_type,
                error_message=str(exc)[:2000],
                experiment_id=experiment_id,
                is_synthetic=is_demo,
            )
        )
        db.flush()
        raise
    except Exception as exc:  # defensive: unexpected SDK failure
        db.add(
            UsageRecord(
                provider=provider,
                model_id=model_id,
                purpose=purpose.value,
                success=False,
                error_type=type(exc).__name__,
                error_message=str(exc)[:2000],
                experiment_id=experiment_id,
                is_synthetic=is_demo,
            )
        )
        db.flush()
        raise ProviderError(str(exc), error_type=type(exc).__name__) from exc

    cost = 0.0
    if not result.is_synthetic and entry is not None:
        cost = estimate_cost_usd(
            result.input_tokens,
            result.output_tokens,
            entry.input_cost_per_mtok,
            entry.output_cost_per_mtok,
        )
    elif not result.is_synthetic and entry is None:
        result.control_limitations.append(
            "Model is not in the catalogue; cost could not be estimated for this call."
        )

    if cacheable and result.text:
        db.merge(
            ResponseCache(
                request_hash=request_hash,
                provider=provider,
                model_id=model_id,
                text=result.text,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                finish_reason=result.finish_reason,
                hit_count=0,
            )
        )

    usage = UsageRecord(
        provider=provider,
        model_id=model_id,
        purpose=purpose.value,
        input_tokens=result.input_tokens or 0,
        output_tokens=result.output_tokens or 0,
        cost_usd=cost,
        latency_ms=result.latency_ms,
        success=True,
        served_from_cache=False,
        experiment_id=experiment_id,
        is_synthetic=result.is_synthetic,
    )
    db.add(usage)
    db.flush()
    return CallOutcome(result=result, cost_usd=cost, usage_record_id=usage.id)


# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> dict:
    """Parse a JSON object from model output, tolerating common wrappers.

    Needed because structured-output support varies by model and because a
    provider may reject the schema parameter and fall back to prompt-level
    instructions.
    """
    candidate = text.strip()
    if not candidate:
        raise StructuredOutputError("Model returned empty output.", error_type="empty_output")

    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    fenced = _FENCE_RE.search(candidate)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = json.loads(candidate[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    raise StructuredOutputError(
        "Could not parse a JSON object from the model's output.",
        error_type="structured_output_parse_failed",
    )


def call_structured(
    db: Session,
    *,
    provider: str,
    model_id: str,
    request: GenerationRequest,
    purpose: CallPurpose,
    experiment_id: str | None = None,
) -> tuple[dict, CallOutcome]:
    """Call a model and return parsed JSON, with one repair attempt.

    The schema is *also* described in the prompt (see
    :func:`explanationlab.transformations.base.schema_instruction`) so that a
    model without native structured output still has a fair chance.
    """
    outcome = call_model(
        db,
        provider=provider,
        model_id=model_id,
        request=request,
        purpose=purpose,
        experiment_id=experiment_id,
    )
    try:
        return extract_json(outcome.result.text), outcome
    except StructuredOutputError:
        repair = GenerationRequest(
            system=request.system,
            user=(
                request.user
                + "\n\n---\nYour previous reply was not valid JSON. Reply with the JSON "
                "object only. No prose, no code fence."
            ),
            max_output_tokens=request.max_output_tokens,
            temperature=request.temperature,
            effort=request.effort,
            json_schema=request.json_schema,
            json_schema_name=request.json_schema_name,
        )
        retry = call_model(
            db,
            provider=provider,
            model_id=model_id,
            request=repair,
            purpose=purpose,
            experiment_id=experiment_id,
        )
        retry.result.control_limitations.append(
            "First attempt returned unparseable JSON; this is the repair attempt."
        )
        return extract_json(retry.result.text), retry
