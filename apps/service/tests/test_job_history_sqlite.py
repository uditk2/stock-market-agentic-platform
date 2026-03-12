from datetime import timedelta

from smap_service.db.job_history import JobRun, SQLiteJobHistoryStore, now_utc


def test_sqlite_history_persists_across_store_instances(tmp_path) -> None:
    db_path = tmp_path / "runtime.sqlite3"
    store_a = SQLiteJobHistoryStore(db_path=db_path, history_retention_days=None)
    started = now_utc()
    finished = started + timedelta(seconds=1)
    store_a.add(
        JobRun(
            job_name="ingest_news",
            started_at=started,
            finished_at=finished,
            status="success",
            records_processed=42,
            error=None,
        )
    )

    store_b = SQLiteJobHistoryStore(db_path=db_path, history_retention_days=None)
    rows = store_b.recent(limit=10)
    assert len(rows) == 1
    assert rows[0].job_name == "ingest_news"
    assert rows[0].records_processed == 42


def test_runtime_state_round_trip(tmp_path) -> None:
    db_path = tmp_path / "runtime.sqlite3"
    store = SQLiteJobHistoryStore(db_path=db_path, history_retention_days=None)
    store.set_runtime_state("last_scheduler_start_utc", "2026-03-12T00:00:00+00:00")
    assert store.get_runtime_state("last_scheduler_start_utc") == "2026-03-12T00:00:00+00:00"
