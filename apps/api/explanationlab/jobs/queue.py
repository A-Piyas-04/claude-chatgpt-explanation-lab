"""Minimal durable job queue.

Deliberately not Celery/Redis/RQ. The brief asks for "a minimal, reliable job
system" without "unnecessary distributed infrastructure", and for a solo
researcher a Postgres (or SQLite) table plus a thread pool is both.

Properties that matter here:

- **Durable**: jobs live in a table, so a restart mid-batch loses nothing.
- **Resumable**: work is tracked per *run*, not per job, so a retried job skips
  runs that already succeeded.
- **Idempotent submission**: ``idempotency_key`` is unique, so a double-clicked
  "Run" button cannot start two batches.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..enums import JobKind, JobStatus
from ..models import Job, utcnow

log = logging.getLogger(__name__)


class DuplicateJobError(RuntimeError):
    def __init__(self, job: Job):
        super().__init__("An identical job is already queued or running.")
        self.job = job


def enqueue(
    db: Session,
    *,
    kind: JobKind,
    payload: dict,
    experiment_id: str | None = None,
    progress_total: int = 0,
    idempotency_key: str | None = None,
    max_attempts: int = 1,
) -> Job:
    if idempotency_key:
        existing = db.execute(
            select(Job).where(Job.idempotency_key == idempotency_key)
        ).scalar_one_or_none()
        if existing is not None and existing.status in {
            JobStatus.QUEUED.value,
            JobStatus.RUNNING.value,
        }:
            raise DuplicateJobError(existing)

    job = Job(
        kind=kind.value,
        status=JobStatus.QUEUED.value,
        payload=payload,
        experiment_id=experiment_id,
        progress_total=progress_total,
        max_attempts=max_attempts,
        idempotency_key=idempotency_key,
    )
    db.add(job)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        existing = db.execute(
            select(Job).where(Job.idempotency_key == idempotency_key)
        ).scalar_one_or_none()
        if existing is not None:
            raise DuplicateJobError(existing) from exc
        raise
    return job


def claim_next(db: Session) -> Job | None:
    """Claim one queued job.

    ``with_for_update(skip_locked=True)`` on Postgres lets several workers run
    safely; SQLite ignores it and relies on its write lock, which is fine for
    the single-process local setup.
    """
    stmt = (
        select(Job)
        .where(Job.status == JobStatus.QUEUED.value)
        .order_by(Job.created_at)
        .limit(1)
    )
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)

    job = db.execute(stmt).scalar_one_or_none()
    if job is None:
        return None

    job.status = JobStatus.RUNNING.value
    job.started_at = utcnow()
    job.attempts += 1
    db.commit()
    return job


def mark_succeeded(db: Session, job: Job) -> None:
    job.status = JobStatus.SUCCEEDED.value
    job.finished_at = utcnow()
    db.commit()


def mark_failed(db: Session, job: Job, error: str) -> None:
    job.error = error[:4000]
    if job.attempts < job.max_attempts:
        job.status = JobStatus.QUEUED.value
        job.started_at = None
    else:
        job.status = JobStatus.FAILED.value
        job.finished_at = utcnow()
    db.commit()


def bump_progress(db: Session, job: Job, *, done: int | None = None) -> None:
    job.progress_done = job.progress_done + 1 if done is None else done
    db.commit()


def cancel(db: Session, job: Job) -> None:
    if job.status == JobStatus.QUEUED.value:
        job.status = JobStatus.CANCELLED.value
        job.finished_at = utcnow()
        db.commit()
