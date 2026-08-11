import threading
import time

from dataclasses import asdict, dataclass, field


JOB_TTL_SECONDS = 60 * 60
MAX_JOBS = 100


@dataclass
class CloneJob:
    job_id: str
    status: str = "running"  # running | done | error
    phase: str = "cloning"  # cloning | indexing
    files_done: int = 0
    files_total: int = 0
    message: str = ""
    error: str = ""
    repository_id: int | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class CloneProgressStore:
    """In-memory, thread-safe progress for long-running clone jobs.

    Jobs are pruned by age and capped in count so the store never grows
    without bound on a small instance.
    """

    def __init__(self):
        self._jobs: dict[str, CloneJob] = {}
        self._lock = threading.Lock()

    def start(self, job_id: str) -> None:
        with self._lock:
            self._jobs[job_id] = CloneJob(job_id=job_id)
            self._prune_locked()

    def update(self, job_id: str, **fields) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in fields.items():
                setattr(job, key, value)
            if "updated_at" not in fields:
                job.updated_at = time.time()

    def get(self, job_id: str) -> CloneJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return CloneJob(**asdict(job))

    def is_running(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            return job is not None and job.status == "running"

    def get_all_ids(self) -> list[str]:
        with self._lock:
            return list(self._jobs.keys())

    def _prune_locked(self) -> None:
        cutoff = time.time() - JOB_TTL_SECONDS
        for job_id in [
            job_id
            for job_id, job in self._jobs.items()
            if job.updated_at < cutoff
        ]:
            del self._jobs[job_id]

        while len(self._jobs) > MAX_JOBS:
            oldest = min(
                self._jobs,
                key=lambda job_id: self._jobs[job_id].updated_at,
            )
            del self._jobs[oldest]


clone_progress = CloneProgressStore()
