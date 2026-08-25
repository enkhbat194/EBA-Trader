from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ExperimentStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"


TERMINAL_EXPERIMENT_STATUSES = frozenset(
    {ExperimentStatus.PASSED, ExperimentStatus.FAILED}
)


@dataclass(frozen=True, slots=True)
class ExperimentClaim:
    experiment_id: str
    worker_id: str
    lease_expires_at_ms: int
    attempt_count: int
    max_attempts: int

    def __post_init__(self) -> None:
        if not self.experiment_id.strip():
            raise ValueError("experiment_id is required")
        if not self.worker_id.strip():
            raise ValueError("worker_id is required")
        if self.lease_expires_at_ms <= 0:
            raise ValueError("lease_expires_at_ms must be positive")
        if self.attempt_count < 1:
            raise ValueError("attempt_count must be >= 1")
        if self.max_attempts < self.attempt_count:
            raise ValueError("max_attempts must be >= attempt_count")
