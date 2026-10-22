"""Health and configuration status. Public, and contains no secrets."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..models import ModelCatalogEntry
from ..providers.catalog import PRICING_VERIFIED_ON
from ..providers.registry import provider_status

router = APIRouter(tags=["system"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
        database_ok = True
    except Exception:
        database_ok = False
    return {"status": "ok" if database_ok else "degraded", "database": database_ok}


@router.get("/status")
def status(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict:
    """What the UI needs to render honest banners about the current mode."""
    catalog_count = len(
        list(db.execute(select(ModelCatalogEntry.id)).scalars())
    )
    payload = settings.public_status()
    payload["provider_status"] = provider_status()
    payload["model_catalog_entries"] = catalog_count
    payload["pricing_verified_on"] = PRICING_VERIFIED_ON
    payload["demo_mode_notice"] = (
        "DEMO MODE: no provider credentials are configured. All generated content "
        "comes from local fixtures, is flagged synthetic, and must never be reported "
        "as a research finding."
        if settings.demo_mode
        else None
    )
    return payload
