from __future__ import annotations

import logging
from dataclasses import dataclass

from apscheduler.schedulers.background import BackgroundScheduler

from smap_service.core.config import RuntimeConfig, resolve_db_path
from smap_service.core.interfaces import MarketFeedClient
from smap_service.core.registry import PluginRegistry
from smap_service.db.job_history import JobRun, SQLiteJobHistoryStore, now_utc
from smap_service.ingestion.jobs import ingest_announcements, ingest_market_bars, ingest_news

logger = logging.getLogger(__name__)


@dataclass
class SchedulerRuntime:
    scheduler: BackgroundScheduler
    history: SQLiteJobHistoryStore


class SchedulerManager:
    def __init__(
        self,
        config: RuntimeConfig,
        registry: PluginRegistry,
        market_client: MarketFeedClient,
    ):
        self._config = config
        self._registry = registry
        self._market_client = market_client
        self._history = SQLiteJobHistoryStore(
            db_path=resolve_db_path(config),
            history_retention_days=config.history_retention_days,
        )
        self._scheduler = BackgroundScheduler()

    def start(self) -> None:
        self._history.set_runtime_state("last_scheduler_start_utc", now_utc().isoformat())
        self._scheduler.add_job(
            self._run_market_job,
            "interval",
            seconds=self._config.scheduler.market_bars_interval_seconds,
            id="market_bars",
            max_instances=1,
            replace_existing=True,
        )
        self._scheduler.add_job(
            self._run_news_job,
            "interval",
            seconds=self._config.scheduler.news_interval_seconds,
            id="news",
            max_instances=1,
            replace_existing=True,
        )
        self._scheduler.add_job(
            self._run_announcement_job,
            "interval",
            seconds=self._config.scheduler.announcements_interval_seconds,
            id="announcements",
            max_instances=1,
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info("scheduler started")

    def stop(self) -> None:
        self._history.set_runtime_state("last_scheduler_stop_utc", now_utc().isoformat())
        self._scheduler.shutdown(wait=False)
        logger.info("scheduler stopped")

    def runtime(self) -> SchedulerRuntime:
        return SchedulerRuntime(scheduler=self._scheduler, history=self._history)

    def _record(self, job_name: str, fn) -> None:
        started = now_utc()
        error = None
        status = "success"
        records = 0
        try:
            result = fn()
            records = result.records_processed
        except Exception as exc:  # pragma: no cover - defensive runtime wrapper
            status = "failed"
            error = str(exc)
            logger.exception("job failed: %s", job_name)
        finished = now_utc()
        self._history.add(
            JobRun(
                job_name=job_name,
                started_at=started,
                finished_at=finished,
                status=status,
                records_processed=records,
                error=error,
            )
        )

    def _run_market_job(self) -> None:
        self._record(
            "ingest_market_bars",
            lambda: ingest_market_bars(self._market_client),
        )

    def _run_news_job(self) -> None:
        self._record(
            "ingest_news",
            lambda: ingest_news(self._registry, self._config.news_providers),
        )

    def _run_announcement_job(self) -> None:
        self._record(
            "ingest_announcements",
            lambda: ingest_announcements(self._registry),
        )
