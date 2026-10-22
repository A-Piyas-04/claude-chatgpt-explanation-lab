"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .db import create_all, session_scope
from .providers.base import ProviderError
from .routers import analytics, catalog, experiments, health, participants, responses, studies

log = logging.getLogger(__name__)

DESCRIPTION = """\
Research platform for studying the human comprehensibility of AI-generated
explanations.

**Evidence categories are kept separate throughout this API.** Automated
diagnostics describe texts, an AI judge offers an opinion, and only human
comprehension results are treated as evidence of understanding. No endpoint
returns a blended "explanation quality" score, by design.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s"
    )

    create_all()
    with session_scope() as db:
        from .seed import seed_all

        counts = seed_all(db)
    log.info("Database ready. Seeded: %s", counts)

    if settings.demo_mode:
        log.warning(
            "DEMO MODE: no provider credentials configured. All generated content will "
            "be local fixtures flagged as synthetic."
        )
    if not settings.auth_enabled:
        log.warning(
            "No RESEARCHER_API_TOKEN set: researcher routes accept local requests only."
        )

    if settings.run_worker_in_api:
        from .jobs.worker import start_background_worker, stop_background_worker

        start_background_worker()
        try:
            yield
        finally:
            stop_background_worker()
    else:
        log.info("In-process worker disabled; run `python -m explanationlab.jobs.worker`.")
        yield


app = FastAPI(
    title="ExplanationLab API",
    description=DESCRIPTION,
    version="0.1.0",
    lifespan=lifespan,
)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(ProviderError)
async def provider_error_handler(_request: Request, exc: ProviderError) -> JSONResponse:
    """Surface real provider errors; never silently substitute a model."""
    status = 402 if exc.error_type == "spend_cap_exceeded" else 502
    return JSONResponse(
        status_code=status,
        content={
            "detail": {
                "message": str(exc),
                "error_type": exc.error_type,
                "provider_status": exc.status,
            }
        },
    )


app.include_router(health.router, prefix="/api")
app.include_router(catalog.router, prefix="/api")
app.include_router(experiments.router, prefix="/api")
app.include_router(responses.router, prefix="/api")
app.include_router(studies.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")

# Public participant routes; no researcher dependency.
app.include_router(participants.router, prefix="/api")


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "name": "ExplanationLab API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health",
        "status": "/api/status",
    }
