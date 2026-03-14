from __future__ import annotations

import json
import sqlite3
import uuid
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

    def list_recent_signals(self, limit: int = 200) -> list[dict[str, object]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT signal_id, symbol, timeframe, as_of, support, resistance,
                       breakout, reversal, consolidation, volume_spike,
                       sentiment_score, fused_score, features_json
                FROM signals
                ORDER BY as_of DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        output: list[dict[str, object]] = []
        for row in rows:
            output.append(
                {
                    "signal_id": row[0],
                    "symbol": row[1],
                    "timeframe": row[2],
                    "as_of": row[3],
                    "support": row[4],
                    "resistance": row[5],
                    "breakout": bool(row[6]),
                    "reversal": bool(row[7]),
                    "consolidation": bool(row[8]),
                    "volume_spike": bool(row[9]),
                    "sentiment_score": row[10],
                    "fused_score": row[11],
                    "features": json.loads(row[12] or "{}"),
                }
            )
        return output

    def save_strategy_artifact(self, strategy_text: str) -> dict[str, object]:
        strategy_text = strategy_text.strip()
        artifact_id = f"strat-{uuid.uuid4().hex[:12]}"
        created_at = now_utc().isoformat()
        with self._lock, self._connect() as conn:
            current = conn.execute("SELECT COALESCE(MAX(version), 0) FROM strategy_artifacts").fetchone()
            version = int(current[0]) + 1
            conn.execute(
                """
                INSERT INTO strategy_artifacts (artifact_id, version, strategy_text, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (artifact_id, version, strategy_text, created_at),
            )
            conn.commit()
        return {
            "artifact_id": artifact_id,
            "version": version,
            "strategy_text": strategy_text,
            "created_at": created_at,
        }

    def latest_strategy_artifact(self) -> dict[str, object] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT artifact_id, version, strategy_text, created_at
                FROM strategy_artifacts
                ORDER BY version DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        return {
            "artifact_id": row[0],
            "version": row[1],
            "strategy_text": row[2],
            "created_at": row[3],
        }

    def list_strategy_artifacts(self, limit: int = 20) -> list[dict[str, object]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT artifact_id, version, strategy_text, created_at
                FROM strategy_artifacts
                ORDER BY version DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "artifact_id": row[0],
                "version": row[1],
                "strategy_text": row[2],
                "created_at": row[3],
            }
            for row in rows
        ]

    def save_recommendations(self, rows: list[dict[str, object]]) -> int:
        if not rows:
            return 0
        with self._lock, self._connect() as conn:
            for row in rows:
                conn.execute(
                    """
                    INSERT INTO recommendations (
                        recommendation_id, symbol, direction, entry_price, stop_loss,
                        target_1, target_2, confidence, rationale, strategy_artifact_id,
                        status, suppress_reason, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(recommendation_id) DO UPDATE SET
                        direction = excluded.direction,
                        entry_price = excluded.entry_price,
                        stop_loss = excluded.stop_loss,
                        target_1 = excluded.target_1,
                        target_2 = excluded.target_2,
                        confidence = excluded.confidence,
                        rationale = excluded.rationale,
                        strategy_artifact_id = excluded.strategy_artifact_id,
                        status = excluded.status,
                        suppress_reason = excluded.suppress_reason
                    """,
                    (
                        row["recommendation_id"],
                        row["symbol"],
                        row["direction"],
                        row["entry_price"],
                        row["stop_loss"],
                        row["target_1"],
                        row.get("target_2"),
                        row["confidence"],
                        row["rationale"],
                        row["strategy_artifact_id"],
                        row["status"],
                        row.get("suppress_reason"),
                        row["created_at"],
                    ),
                )
                links = row.get("signal_ids", [])
                for signal_id in links:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO recommendation_signal_links (recommendation_id, signal_id)
                        VALUES (?, ?)
                        """,
                        (row["recommendation_id"], signal_id),
                    )
            conn.commit()
        return len(rows)

    def list_recommendations(self, query: str | None = None, include_suppressed: bool = False) -> list[dict[str, object]]:
        with self._lock, self._connect() as conn:
            sql = """
                SELECT recommendation_id, symbol, direction, entry_price, stop_loss,
                       target_1, target_2, confidence, rationale, strategy_artifact_id,
                       status, suppress_reason, created_at
                FROM recommendations
            """
            clauses: list[str] = []
            params: list[object] = []
            if not include_suppressed:
                clauses.append("status = 'published'")
            if query:
                clauses.append("LOWER(symbol) LIKE ?")
                params.append(f"%{query.strip().lower()}%")
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            sql += " ORDER BY confidence DESC, created_at DESC LIMIT 200"
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [
            {
                "recommendation_id": row[0],
                "symbol": row[1],
                "direction": row[2],
                "entry_price": row[3],
                "stop_loss": row[4],
                "target_1": row[5],
                "target_2": row[6],
                "confidence": row[7],
                "rationale": row[8],
                "strategy_artifact_id": row[9],
                "status": row[10],
                "suppress_reason": row[11],
                "created_at": row[12],
            }
            for row in rows
        ]

    def get_recommendation(self, recommendation_id: str) -> dict[str, object] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT recommendation_id, symbol, direction, entry_price, stop_loss,
                       target_1, target_2, confidence, rationale, strategy_artifact_id,
                       status, suppress_reason, created_at
                FROM recommendations
                WHERE recommendation_id = ?
                """,
                (recommendation_id,),
            ).fetchone()
            link_rows = conn.execute(
                "SELECT signal_id FROM recommendation_signal_links WHERE recommendation_id = ?",
                (recommendation_id,),
            ).fetchall()
        if row is None:
            return None
        return {
            "recommendation_id": row[0],
            "symbol": row[1],
            "direction": row[2],
            "entry_price": row[3],
            "stop_loss": row[4],
            "target_1": row[5],
            "target_2": row[6],
            "confidence": row[7],
            "rationale": row[8],
            "strategy_artifact_id": row[9],
            "status": row[10],
            "suppress_reason": row[11],
            "created_at": row[12],
            "signal_ids": [link[0] for link in link_rows],
        }

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
                CREATE TABLE IF NOT EXISTS strategy_artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL UNIQUE,
                    strategy_text TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS recommendations (
                    recommendation_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    target_1 REAL NOT NULL,
                    target_2 REAL,
                    confidence REAL NOT NULL,
                    rationale TEXT NOT NULL,
                    strategy_artifact_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    suppress_reason TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS recommendation_signal_links (
                    recommendation_id TEXT NOT NULL,
                    signal_id TEXT NOT NULL,
                    PRIMARY KEY (recommendation_id, signal_id)
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
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_recommendations_symbol
                ON recommendations (symbol, confidence DESC)
                """
            )
            conn.commit()


def now_utc() -> datetime:
    return datetime.now(UTC)
