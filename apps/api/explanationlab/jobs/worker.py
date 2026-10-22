"""Job worker.

Runs either inside the API process (``RUN_WORKER_IN_API=true``, the default for
local development) or standalone:

    python -m explanationlab.jobs.worker

A single failing run does not fail the batch: the run is marked failed with its
error recorded, the batch carries on, and the researcher can retry just the
failures.
"""

from __future__ import annotations

import logging
import threading
import time

from sqlalchemy import select

from ..config import get_settings
from ..db import SessionLocal, session_scope
from ..enums import ExperimentStatus, JobKind, JobStatus, RunStatus
from ..experiments import orchestrator
from ..models import Experiment, ExperimentRun, Job, utcnow
from . import queue

log = logging.getLogger(__name__)

_stop_event = threading.Event()
_thread: threading.Thread | None = None

POLL_SECONDS = 1.5


def run_job(job_id: str) -> None:
    """Execute one job to completion."""
    with session_scope() as db:
        job = db.get(Job, job_id)
        if job is None:
            return
        kind = job.kind
        payload = dict(job.payload or {})

    if kind == JobKind.EXPERIMENT_BATCH.value:
        _run_experiment_batch(job_id, payload)
    elif kind == JobKind.JUDGE_EVALUATION.value:
        _run_judge_batch(job_id, payload)
    else:
        with session_scope() as db:
            job = db.get(Job, job_id)
            if job:
                queue.mark_failed(db, job, f"Unknown job kind '{kind}'.")


def _run_experiment_batch(job_id: str, payload: dict) -> None:
    experiment_id = payload.get("experiment_id")
    retry_failed_only = bool(payload.get("retry_failed_only"))

    with session_scope() as db:
        experiment = db.get(Experiment, experiment_id)
        if experiment is None:
            job = db.get(Job, job_id)
            if job:
                queue.mark_failed(db, job, f"Experiment {experiment_id} not found.")
            return
        experiment.status = ExperimentStatus.RUNNING.value
        experiment.started_at = experiment.started_at or utcnow()

        statuses = (
            [RunStatus.FAILED.value]
            if retry_failed_only
            else [RunStatus.PENDING.value, RunStatus.FAILED.value]
        )
        run_ids = [
            r.id
            for r in db.execute(
                select(ExperimentRun)
                .where(
                    ExperimentRun.experiment_id == experiment_id,
                    ExperimentRun.status.in_(statuses),
                )
                .order_by(ExperimentRun.created_at)
            ).scalars()
        ]
        job = db.get(Job, job_id)
        if job:
            job.progress_total = len(run_ids)
            job.progress_done = 0

    failures = 0
    for run_id in run_ids:
        if _stop_event.is_set():
            break
        try:
            with session_scope() as db:
                run = db.get(ExperimentRun, run_id)
                if run is None or run.status == RunStatus.SUCCEEDED.value:
                    continue
                orchestrator.execute_run(db, run)
        except Exception as exc:  # one bad run must not sink the batch
            failures += 1
            log.warning("Run %s failed: %s", run_id, exc)
        finally:
            with session_scope() as db:
                job = db.get(Job, job_id)
                if job:
                    job.progress_done += 1

    with session_scope() as db:
        experiment = db.get(Experiment, experiment_id)
        if experiment is not None:
            orchestrator.refresh_experiment_status(db, experiment)
        job = db.get(Job, job_id)
        if job:
            if failures and failures == job.progress_total:
                queue.mark_failed(db, job, f"All {failures} run(s) failed. See run errors.")
            else:
                if failures:
                    job.error = f"{failures} of {job.progress_total} run(s) failed."
                queue.mark_succeeded(db, job)


def _run_judge_batch(job_id: str, payload: dict) -> None:
    from ..evaluation.judge import judge_response
    from ..models import Response

    response_ids: list[str] = list(payload.get("response_ids") or [])
    provider = payload.get("provider")
    model_id = payload.get("model_id")
    effort = payload.get("effort")

    with session_scope() as db:
        job = db.get(Job, job_id)
        if job:
            job.progress_total = len(response_ids)
            job.progress_done = 0

    failures = 0
    for response_id in response_ids:
        if _stop_event.is_set():
            break
        try:
            with session_scope() as db:
                response = db.get(Response, response_id)
                if response is None:
                    continue
                question = response.question
                profile = response.learner_profile
                judge_response(
                    db,
                    response,
                    provider=provider,
                    model_id=model_id,
                    learner_description=(
                        f"{profile.level}: {profile.description}" if profile else "unspecified"
                    ),
                    question_text=question.text if question else "",
                    effort=effort,
                )
        except Exception as exc:
            failures += 1
            log.warning("Judging response %s failed: %s", response_id, exc)
        finally:
            with session_scope() as db:
                job = db.get(Job, job_id)
                if job:
                    job.progress_done += 1

    with session_scope() as db:
        job = db.get(Job, job_id)
        if job:
            if failures and failures == job.progress_total:
                queue.mark_failed(db, job, f"All {failures} evaluation(s) failed.")
            else:
                if failures:
                    job.error = f"{failures} of {job.progress_total} evaluation(s) failed."
                queue.mark_succeeded(db, job)


# ---------------------------------------------------------------------------
# Loop
# ---------------------------------------------------------------------------


def _loop() -> None:
    log.info("ExplanationLab job worker started.")
    while not _stop_event.is_set():
        job_id: str | None = None
        db = SessionLocal()
        try:
            job = queue.claim_next(db)
            job_id = job.id if job else None
        except Exception as exc:  # pragma: no cover - transient DB issues
            log.warning("Could not claim a job: %s", exc)
        finally:
            db.close()

        if job_id is None:
            _stop_event.wait(POLL_SECONDS)
            continue

        try:
            run_job(job_id)
        except Exception as exc:
            log.exception("Job %s crashed: %s", job_id, exc)
            with session_scope() as db:
                job = db.get(Job, job_id)
                if job and job.status == JobStatus.RUNNING.value:
                    queue.mark_failed(db, job, str(exc))
    log.info("ExplanationLab job worker stopped.")


def start_background_worker() -> None:
    """Start the in-process worker thread (idempotent)."""
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_loop, name="explab-worker", daemon=True)
    _thread.start()


def stop_background_worker(timeout: float = 5.0) -> None:
    _stop_event.set()
    if _thread is not None:
        _thread.join(timeout=timeout)


def main() -> None:  # pragma: no cover - entry point
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s"
    )
    settings = get_settings()
    log.info(
        "Worker starting (demo_mode=%s, concurrency=%s)", settings.demo_mode, settings.worker_concurrency
    )
    try:
        _loop()
    except KeyboardInterrupt:
        _stop_event.set()
        log.info("Interrupted; shutting down.")


if __name__ == "__main__":  # pragma: no cover
    main()
