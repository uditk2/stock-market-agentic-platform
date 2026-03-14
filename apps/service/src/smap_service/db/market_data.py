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

    def list_recent_bars_by_symbol(self, limit_per_symbol: int = 32) -> dict[str, list[dict[str, object]]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT symbol, timeframe, as_of, open, high, low, close, volume
                FROM market_bars
                ORDER BY symbol ASC, as_of DESC
                """
            ).fetchall()
        grouped: dict[str, list[dict[str, object]]] = {}
        for row in rows:
            symbol = str(row[0])
            bucket = grouped.setdefault(symbol, [])
            if len(bucket) >= limit_per_symbol:
                continue
            bucket.append(
                {
                    "symbol": symbol,
                    "timeframe": row[1],
                    "as_of": row[2],
                    "open": row[3],
                    "high": row[4],
                    "low": row[5],
                    "close": row[6],
                    "volume": row[7],
                }
            )
        return grouped

    def list_recent_news_items(self, limit: int = 300) -> list[dict[str, object]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT source, external_id, published_at, headline, body, symbols_json
                FROM news_items
                ORDER BY published_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        output: list[dict[str, object]] = []
        for row in rows:
            output.append(
                {
                    "source": row[0],
                    "external_id": row[1],
                    "published_at": row[2],
                    "headline": row[3],
                    "body": row[4],
                    "symbols": json.loads(row[5] or "[]"),
                }
            )
        return output

    def save_signals(self, signals: list[object]) -> int:
        if not signals:
            return 0
        with self._lock, self._connect() as conn:
            rows = [
                (
                    item.signal_id,
                    item.symbol,
                    item.timeframe,
                    item.as_of,
                    item.support,
                    item.resistance,
                    int(item.breakout),
                    int(item.reversal),
                    int(item.consolidation),
                    int(item.volume_spike),
                    item.sentiment_score,
                    item.fused_score,
                    item.features_json,
                    now_utc().isoformat(),
                )
                for item in signals
            ]
            conn.executemany(
                """
                INSERT INTO signals (
                    signal_id, symbol, timeframe, as_of, support, resistance,
                    breakout, reversal, consolidation, volume_spike,
                    sentiment_score, fused_score, features_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(signal_id) DO UPDATE SET
                    support = excluded.support,
                    resistance = excluded.resistance,
                    breakout = excluded.breakout,
                    reversal = excluded.reversal,
                    consolidation = excluded.consolidation,
                    volume_spike = excluded.volume_spike,
                    sentiment_score = excluded.sentiment_score,
                    fused_score = excluded.fused_score,
                    features_json = excluded.features_json
                """,
                rows,
            )
            conn.commit()
        return len(signals)

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
                CREATE TABLE IF NOT EXISTS signals (
                    signal_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    as_of TEXT NOT NULL,
                    support REAL NOT NULL,
                    resistance REAL NOT NULL,
                    breakout INTEGER NOT NULL,
                    reversal INTEGER NOT NULL,
                    consolidation INTEGER NOT NULL,
                    volume_spike INTEGER NOT NULL,
                    sentiment_score REAL NOT NULL,
                    fused_score REAL NOT NULL,
                    features_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
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
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_signals_symbol_asof
                ON signals (symbol, as_of DESC)
                """
            )
            conn.commit()


def now_utc() -> datetime:
    return datetime.now(UTC)
