from __future__ import annotations

import sqlite3
import json
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from threading import Lock
from typing import Any


@dataclass
class JobRun:
    job_name: str
    started_at: datetime
    finished_at: datetime
    status: str
    records_processed: int
    error: str | None = None
    connector: str | None = None
    duration_ms: int = 0
    attribution: dict[str, Any] | None = None


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
                    error,
                    connector,
                    duration_ms,
                    attribution_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.job_name,
                    run.started_at.isoformat(),
                    run.finished_at.isoformat(),
                    run.status,
                    run.records_processed,
                    run.error,
                    run.connector,
                    run.duration_ms,
                    json.dumps(run.attribution, sort_keys=True) if run.attribution is not None else None,
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
                    error,
                    connector,
                    duration_ms,
                    attribution_json
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
                connector=row[6],
                duration_ms=row[7] or 0,
                attribution=json.loads(row[8]) if row[8] else None,
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
                    error TEXT,
                    connector TEXT,
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    attribution_json TEXT
                )
                """
            )
            self._ensure_column(conn, "job_runs", "connector", "TEXT")
            self._ensure_column(conn, "job_runs", "duration_ms", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "job_runs", "attribution_json", "TEXT")
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

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, ddl_suffix: str) -> None:
        existing = conn.execute(f"PRAGMA table_info({table})").fetchall()
        names = {row[1] for row in existing}
        if column not in names:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_suffix}")


def now_utc() -> datetime:
    return datetime.now(UTC)
