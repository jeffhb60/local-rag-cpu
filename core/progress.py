from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4


VALID_STATUSES = {"queued", "running", "succeeded", "failed", "cancelled"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobState:
    job_id: str
    status: str = "queued"
    message: str = "Queued"
    current: int = 0
    total: int = 0
    logs: list[str] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    finished_at: str | None = None


class JobManager:
    """
    Lightweight in-memory job tracker.

    Good for local development.

    Important:
    - Use one Uvicorn worker.
    - Server reloads clear jobs.
    - For production, use Redis, a database, RQ, Celery, or Dramatiq.
    """

    def __init__(self, max_logs: int = 500):
        self._jobs: dict[str, JobState] = {}
        self._lock = Lock()
        self._max_logs = max_logs

    def create(self, total: int = 0, message: str = "Queued") -> str:
        job_id = str(uuid4())
        now = utc_now_iso()

        job = JobState(
            job_id=job_id,
            status="queued",
            message=message,
            current=0,
            total=max(total, 0),
            logs=[message],
            created_at=now,
            updated_at=now,
        )

        with self._lock:
            self._jobs[job_id] = job

        print(f"[jobs] created {job_id}: {message}", flush=True)
        return job_id

    def update(
        self,
        job_id: str,
        *,
        status: str | None = None,
        message: str | None = None,
        current: int | None = None,
        total: int | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)

            if job is None:
                print(f"[jobs] update ignored; missing job_id={job_id}", flush=True)
                return

            if status is not None:
                if status not in VALID_STATUSES:
                    raise ValueError(f"Invalid job status: {status}")
                job.status = status

            if total is not None:
                job.total = max(total, 0)

            if current is not None:
                job.current = max(current, 0)

                if job.total > 0:
                    job.current = min(job.current, job.total)

            if message is not None:
                job.message = message
                job.logs.append(message)

                if len(job.logs) > self._max_logs:
                    job.logs = job.logs[-self._max_logs :]

            job.updated_at = utc_now_iso()
            log_status = job.status

        if message is not None:
            print(f"[jobs] {job_id}: {log_status} - {message}", flush=True)

    def succeed(self, job_id: str, result: dict[str, Any] | None = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)

            if job is None:
                print(f"[jobs] succeed ignored; missing job_id={job_id}", flush=True)
                return

            now = utc_now_iso()

            job.status = "succeeded"
            job.message = "Complete"
            job.result = result or {}
            job.error = None
            job.current = job.total if job.total > 0 else job.current
            job.finished_at = now
            job.updated_at = now
            job.logs.append("Complete")

            if len(job.logs) > self._max_logs:
                job.logs = job.logs[-self._max_logs :]

        print(f"[jobs] succeeded {job_id}", flush=True)

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)

            if job is None:
                print(f"[jobs] fail ignored; missing job_id={job_id}: {error}", flush=True)
                return

            now = utc_now_iso()

            job.status = "failed"
            job.message = "Failed"
            job.error = str(error)
            job.finished_at = now
            job.updated_at = now
            job.logs.append(f"Failed: {error}")

            if len(job.logs) > self._max_logs:
                job.logs = job.logs[-self._max_logs :]

        print(f"[jobs] failed {job_id}: {error}", flush=True)

    def cancel(self, job_id: str, message: str = "Cancelled") -> bool:
        with self._lock:
            job = self._jobs.get(job_id)

            if job is None:
                print(f"[jobs] cancel ignored; missing job_id={job_id}", flush=True)
                return False

            now = utc_now_iso()

            job.status = "cancelled"
            job.message = message
            job.finished_at = now
            job.updated_at = now
            job.logs.append(message)

            if len(job.logs) > self._max_logs:
                job.logs = job.logs[-self._max_logs :]

        print(f"[jobs] cancelled {job_id}: {message}", flush=True)
        return True

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)

            if job is None:
                print(f"[jobs] get missing job_id={job_id}", flush=True)
                return None

            return asdict(job)

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            jobs = list(self._jobs.values())
            jobs.sort(key=lambda job: job.created_at, reverse=True)
            return [asdict(job) for job in jobs]

    def clear_finished(self) -> int:
        finished_statuses = {"succeeded", "failed", "cancelled"}

        with self._lock:
            finished_job_ids = [
                job_id
                for job_id, job in self._jobs.items()
                if job.status in finished_statuses
            ]

            for job_id in finished_job_ids:
                del self._jobs[job_id]

        print(f"[jobs] cleared {len(finished_job_ids)} finished job(s)", flush=True)
        return len(finished_job_ids)


jobs = JobManager()