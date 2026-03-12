from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from threading import Lock


@dataclass
class JobRun:
    job_name: str
    started_at: datetime
    finished_at: datetime
    status: str
    records_processed: int
    error: str | None = None


class SQLiteJobHistoryStore:
    def __init__(self, db_path: Path, history_retention_days: int | None = None):
        self._db_path = db_path
        self._history_retention_days = history_retention_days
        self._lock = Lock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def add(self, run: JobRun) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO job_runs (
                    job_name,
                    started_at,
                    finished_at,
                    status,
                    records_processed,
                    error
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run.job_name,
                    run.started_at.isoformat(),
                    run.finished_at.isoformat(),
                    run.status,
                    run.records_processed,
                    run.error,
                ),
            )
            if self._history_retention_days is not None and self._history_retention_days > 0:
                conn.execute(
                    """
                    DELETE FROM job_runs
                    WHERE finished_at < datetime('now', ?)
                    """,
                    (f"-{self._history_retention_days} days",),
                )
            conn.commit()

    def recent(self, limit: int = 50) -> list[JobRun]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    job_name,
                    started_at,
                    finished_at,
                    status,
                    records_processed,
                    error
                FROM job_runs
                ORDER BY finished_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            JobRun(
                job_name=row[0],
                started_at=datetime.fromisoformat(row[1]),
                finished_at=datetime.fromisoformat(row[2]),
                status=row[3],
                records_processed=row[4],
                error=row[5],
            )
            for row in rows
        ]

    def set_runtime_state(self, key: str, value: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runtime_state (state_key, state_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(state_key) DO UPDATE SET
                    state_value = excluded.state_value,
                    updated_at = excluded.updated_at
                """,
                (key, value, now_utc().isoformat()),
            )
            conn.commit()

    def get_runtime_state(self, key: str) -> str | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT state_value FROM runtime_state WHERE state_key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return row[0]

    def db_path(self) -> Path:
        return self._db_path

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS job_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_name TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    records_processed INTEGER NOT NULL,
                    error TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_job_runs_finished_at
                ON job_runs (finished_at DESC)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_state (
                    state_key TEXT PRIMARY KEY,
                    state_value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()


def now_utc() -> datetime:
    return datetime.now(UTC)
