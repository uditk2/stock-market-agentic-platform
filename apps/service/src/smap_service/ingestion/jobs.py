from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from smap_service.core.interfaces import MarketFeedClient, NewsItem
from smap_service.core.registry import PluginRegistry
from smap_service.core.signals import compute_signals_from_store
from smap_service.db.market_data import SQLiteMarketDataStore

logger = logging.getLogger(__name__)


@dataclass
class JobResult:
    job_name: str
    status: str
    records_processed: int
    error: str | None = None
    connector: str | None = None
    attribution: dict[str, Any] | None = None


def ingest_market_bars(
    market_client: MarketFeedClient,
    market_data_store: SQLiteMarketDataStore | None = None,
) -> JobResult:
    symbols = _resolve_symbol_universe(market_client)
    bars = market_client.fetch_latest_bars(symbols=symbols)
    persisted = len(bars)
    if market_data_store is not None:
        persisted = market_data_store.save_market_bars(bars)
    logger.info(
        "market bars ingestion tick connector=%s records=%s",
        market_client.name,
        persisted,
    )
    return JobResult(
        job_name="ingest_market_bars",
        status="success",
        records_processed=persisted,
        connector=market_client.name,
        attribution={"symbols_requested": len(symbols), "symbols_source": "dynamic_or_fallback"},
    )


def ingest_news(
    registry: PluginRegistry,
    enabled: list[str],
    market_data_store: SQLiteMarketDataStore | None = None,
) -> JobResult:
    count = 0
    provider_counts: dict[str, int] = {}
    for provider_name in enabled:
        provider = registry.news_providers.get(provider_name)
        if not provider:
            continue
        items = _map_news_symbols(provider.fetch())
        fetched = len(items)
        if market_data_store is not None:
            market_data_store.save_news_items(items=items, channel=provider_name)
        count += fetched
        provider_counts[provider_name] = fetched
    logger.info("news ingestion tick providers=%s records=%s", enabled, count)
    return JobResult(
        job_name="ingest_news",
        status="success",
        records_processed=count,
        connector="news_registry",
        attribution={
            "providers_enabled": enabled,
            "provider_counts": provider_counts,
        },
    )


def ingest_announcements(
    registry: PluginRegistry,
    market_data_store: SQLiteMarketDataStore | None = None,
) -> JobResult:
    provider = registry.news_providers.get("nse_announcements")
    items = _map_news_symbols(provider.fetch()) if provider else []
    if market_data_store is not None:
        market_data_store.save_news_items(items=items, channel="nse_announcements")
    count = len(items)
    logger.info("announcement ingestion tick records=%s", count)
    return JobResult(
        job_name="ingest_announcements",
        status="success",
        records_processed=count,
        connector="nse_announcements",
        attribution={"provider_available": bool(provider)},
    )


def compute_signals(market_data_store: SQLiteMarketDataStore) -> JobResult:
    signals = compute_signals_from_store(market_data_store)
    persisted = market_data_store.save_signals(signals)
    return JobResult(
        job_name="compute_signals",
        status="success",
        records_processed=persisted,
        connector="signal_engine",
        attribution={"symbols_scored": len({item.symbol for item in signals})},
    )


def _resolve_symbol_universe(market_client: MarketFeedClient) -> list[str]:
    default = ["NIFTY-FUT", "BANKNIFTY-FUT", "RELIANCE-FUT", "TCS-FUT"]
    resolver = getattr(market_client, "list_active_stock_futures_symbols", None)
    if callable(resolver):
        try:
            symbols = resolver()
            if symbols:
                return symbols
        except Exception as exc:  # pragma: no cover - runtime wrapper
            logger.warning("symbol universe resolver failed: %s", exc)
    return default


def _map_news_symbols(items: list[NewsItem]) -> list[NewsItem]:
    if not items:
        return items
    mapped: list[NewsItem] = []
    for item in items:
        mapped.append(
            NewsItem(
                source=item.source,
                external_id=item.external_id,
                headline=item.headline,
                body=item.body,
                symbols=item.symbols,
                published_at=item.published_at,
            )
        )
    return mapped
