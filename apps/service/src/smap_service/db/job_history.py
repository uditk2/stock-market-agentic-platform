from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC


@dataclass
class JobRun:
    job_name: str
    started_at: datetime
    finished_at: datetime
    status: str
    records_processed: int
    error: str | None = None


@dataclass
class InMemoryJobHistoryStore:
    runs: list[JobRun] = field(default_factory=list)

    def add(self, run: JobRun) -> None:
        self.runs.append(run)

    def recent(self, limit: int = 50) -> list[JobRun]:
        return list(reversed(self.runs[-limit:]))


def now_utc() -> datetime:
    return datetime.now(UTC)
