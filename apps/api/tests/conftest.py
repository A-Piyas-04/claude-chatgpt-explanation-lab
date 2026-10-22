"""Test fixtures.

Every test runs against a fresh SQLite database with no provider credentials,
so the whole suite exercises demo mode and never makes a network call or spends
money.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Must be set before explanationlab.config is imported anywhere.
_TMP = Path(tempfile.mkdtemp(prefix="explab-test-"))
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{(_TMP / 'test.sqlite3').as_posix()}"
os.environ["OPENAI_API_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["RESEARCHER_API_TOKEN"] = ""
os.environ["RUN_WORKER_IN_API"] = "false"
os.environ["ENABLE_RESPONSE_CACHE"] = "false"
os.environ["DAILY_SPEND_CAP_USD"] = "1000"


@pytest.fixture(scope="session")
def _db_ready():
    from explanationlab.db import create_all, session_scope
    from explanationlab.seed import seed_all

    create_all()
    with session_scope() as db:
        seed_all(db)
    return True


@pytest.fixture
def db(_db_ready):
    from explanationlab.db import SessionLocal

    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


@pytest.fixture
def client(_db_ready):
    from fastapi.testclient import TestClient

    from explanationlab.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def question(db):
    from sqlalchemy import select

    from explanationlab.models import ResearchQuestion

    return db.execute(select(ResearchQuestion).limit(1)).scalar_one()


@pytest.fixture
def profile(db):
    from sqlalchemy import select

    from explanationlab.models import LearnerProfile

    return db.execute(
        select(LearnerProfile).where(LearnerProfile.level == "intermediate").limit(1)
    ).scalars().first()
