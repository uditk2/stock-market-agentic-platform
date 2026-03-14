from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from smap_service.db.market_data import SQLiteMarketDataStore


@dataclass
class SignalRecord:
    signal_id: str
    symbol: str
    timeframe: str
    as_of: str
    support: float
    resistance: float
    breakout: bool
    reversal: bool
    consolidation: bool
    volume_spike: bool
    sentiment_score: float
    fused_score: float
    features_json: str


def compute_signals_from_store(store: SQLiteMarketDataStore) -> list[SignalRecord]:
    bars_by_symbol = store.list_recent_bars_by_symbol(limit_per_symbol=32)
    news_items = store.list_recent_news_items(limit=300)
    if not bars_by_symbol:
        return []

    news_by_symbol: dict[str, list[dict[str, object]]] = {}
    for item in news_items:
        for symbol in item.get("symbols", []):
            news_by_symbol.setdefault(str(symbol), []).append(item)

    rows: list[SignalRecord] = []
    for symbol, bars in bars_by_symbol.items():
        if len(bars) < 3:
            continue
        bars_sorted = sorted(bars, key=lambda row: str(row["as_of"]))
        closes = [float(row["close"]) for row in bars_sorted]
        highs = [float(row["high"]) for row in bars_sorted]
        lows = [float(row["low"]) for row in bars_sorted]
        volumes = [float(row["volume"]) for row in bars_sorted]
        latest = bars_sorted[-1]

        support = min(lows[-20:])
        resistance = max(highs[-20:])
        previous_resistance = max(highs[-21:-1]) if len(highs) > 21 else max(highs[:-1])
        breakout = closes[-1] > previous_resistance
        reversal = len(closes) >= 3 and closes[-3] > closes[-2] < closes[-1]
        tail = closes[-8:] if len(closes) >= 8 else closes
        consolidation = ((max(tail) - min(tail)) / closes[-1]) < 0.01 if closes[-1] else False
        avg_volume = (sum(volumes[:-1]) / max(1, len(volumes) - 1)) if len(volumes) > 1 else volumes[-1]
        volume_spike = volumes[-1] > (avg_volume * 1.8 if avg_volume else volumes[-1] + 1)

        symbol_news = news_by_symbol.get(symbol, [])
        sentiment_score = _sentiment_proxy(symbol_news)
        fused_score = _fused_score(
            breakout=breakout,
            reversal=reversal,
            consolidation=consolidation,
            volume_spike=volume_spike,
            sentiment_score=sentiment_score,
        )
        features = {
            "support": support,
            "resistance": resistance,
            "breakout": breakout,
            "reversal": reversal,
            "consolidation": consolidation,
            "volume_spike": volume_spike,
            "sentiment_score": sentiment_score,
            "news_item_count": len(symbol_news),
        }
        signal_id = _stable_signal_id(symbol=symbol, timeframe="1m", as_of=str(latest["as_of"]), features=features)
        rows.append(
            SignalRecord(
                signal_id=signal_id,
                symbol=symbol,
                timeframe="1m",
                as_of=str(latest["as_of"]),
                support=support,
                resistance=resistance,
                breakout=breakout,
                reversal=reversal,
                consolidation=consolidation,
                volume_spike=volume_spike,
                sentiment_score=sentiment_score,
                fused_score=fused_score,
                features_json=json.dumps(features, sort_keys=True),
            )
        )
    return rows


def _stable_signal_id(symbol: str, timeframe: str, as_of: str, features: dict[str, object]) -> str:
    blob = json.dumps(
        {
            "symbol": symbol,
            "timeframe": timeframe,
            "as_of": as_of,
            "features": features,
        },
        sort_keys=True,
    ).encode("utf-8")
    digest = hashlib.sha256(blob).hexdigest()[:24]
    return f"sig-{digest}"


def _sentiment_proxy(items: list[dict[str, object]]) -> float:
    if not items:
        return 0.0
    positive_terms = ("gain", "up", "strong", "beat", "growth", "surge")
    negative_terms = ("down", "weak", "fall", "drop", "miss", "decline")
    score = 0.0
    for item in items:
        text = f"{item.get('headline', '')} {item.get('body', '')}".lower()
        score += sum(1 for term in positive_terms if term in text)
        score -= sum(1 for term in negative_terms if term in text)
    return max(-1.0, min(1.0, score / max(1, len(items) * 2)))


def _fused_score(
    breakout: bool,
    reversal: bool,
    consolidation: bool,
    volume_spike: bool,
    sentiment_score: float,
) -> float:
    raw = (
        (0.35 if breakout else 0.0)
        + (0.2 if reversal else 0.0)
        + (0.15 if consolidation else 0.0)
        + (0.2 if volume_spike else 0.0)
        + (0.1 * sentiment_score)
    )
    return round(max(0.0, min(1.0, raw)), 4)
