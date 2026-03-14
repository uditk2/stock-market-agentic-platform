from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock

from smap_service.core.interfaces import MarketBar, NewsItem


class SQLiteMarketDataStore:
    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._lock = Lock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def save_market_bars(self, bars: list[MarketBar]) -> int:
        if not bars:
            return 0
        with self._lock, self._connect() as conn:
            rows = [
                (
                    bar.symbol,
                    bar.timeframe,
                    bar.as_of,
                    bar.open,
                    bar.high,
                    bar.low,
                    bar.close,
                    bar.volume,
                    now_utc().isoformat(),
                )
                for bar in bars
            ]
            conn.executemany(
                """
                INSERT INTO market_bars (
                    symbol, timeframe, as_of, open, high, low, close, volume, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, timeframe, as_of) DO UPDATE SET
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    close = excluded.close,
                    volume = excluded.volume,
                    ingested_at = excluded.ingested_at
                """,
                rows,
            )
            conn.execute(
                "DELETE FROM market_bars WHERE ingested_at < ?",
                ((now_utc() - timedelta(days=120)).isoformat(),),
            )
            conn.commit()
        return len(bars)

    def save_news_items(self, items: list[NewsItem], channel: str) -> int:
        if not items:
            return 0
        with self._lock, self._connect() as conn:
            rows = [
                (
                    channel,
                    item.source,
                    item.external_id,
                    item.published_at,
                    item.headline,
                    item.body,
                    json.dumps(item.symbols, sort_keys=True),
                    now_utc().isoformat(),
                )
                for item in items
            ]
            conn.executemany(
                """
                INSERT INTO news_items (
                    channel, source, external_id, published_at, headline, body, symbols_json, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(channel, external_id) DO UPDATE SET
                    source = excluded.source,
                    published_at = excluded.published_at,
                    headline = excluded.headline,
                    body = excluded.body,
                    symbols_json = excluded.symbols_json,
                    ingested_at = excluded.ingested_at
                """,
                rows,
            )
            conn.commit()
        return len(items)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS market_bars (
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    as_of TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    ingested_at TEXT NOT NULL,
                    PRIMARY KEY (symbol, timeframe, as_of)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS news_items (
                    channel TEXT NOT NULL,
                    source TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    headline TEXT NOT NULL,
                    body TEXT NOT NULL,
                    symbols_json TEXT NOT NULL,
                    ingested_at TEXT NOT NULL,
                    PRIMARY KEY (channel, external_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_market_bars_symbol_time
                ON market_bars (symbol, timeframe, as_of DESC)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_news_items_channel_time
                ON news_items (channel, published_at DESC)
                """
            )
            conn.commit()


def now_utc() -> datetime:
    return datetime.now(UTC)
