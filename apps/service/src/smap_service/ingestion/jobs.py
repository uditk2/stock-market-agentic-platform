from __future__ import annotations

import logging
from dataclasses import dataclass

from smap_service.core.registry import PluginRegistry

logger = logging.getLogger(__name__)


@dataclass
class JobResult:
    job_name: str
    status: str
    records_processed: int
    error: str | None = None


def ingest_market_bars() -> JobResult:
    # Phase 1 scaffold; real Kotak integration in next sprint.
    logger.info("market bars ingestion tick")
    return JobResult(job_name="ingest_market_bars", status="success", records_processed=0)


def ingest_news(registry: PluginRegistry, enabled: list[str]) -> JobResult:
    count = 0
    for provider_name in enabled:
        provider = registry.news_providers.get(provider_name)
        if not provider:
            continue
        count += len(provider.fetch())
    logger.info("news ingestion tick providers=%s records=%s", enabled, count)
    return JobResult(job_name="ingest_news", status="success", records_processed=count)


def ingest_announcements(registry: PluginRegistry) -> JobResult:
    provider = registry.news_providers.get("nse_announcements")
    count = len(provider.fetch()) if provider else 0
    logger.info("announcement ingestion tick records=%s", count)
    return JobResult(job_name="ingest_announcements", status="success", records_processed=count)
