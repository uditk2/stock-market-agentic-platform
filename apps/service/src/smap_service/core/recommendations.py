from __future__ import annotations

import calendar
import hashlib
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone

from smap_service.db.market_data import SQLiteMarketDataStore


@dataclass
class Recommendation:
    recommendation_id: str
    symbol: str
    confidence: float
    direction: str
    summary: str
    tabs: dict[str, list[str]]
    entry_price: float
    stop_loss: float
    target_1: float
    target_2: float | None
    strategy_artifact_id: str
    signal_ids: list[str]
    status: str
    suppress_reason: str | None
    close_reason: str | None
    close_price: float | None
    realized_pnl_per_lot: float | None
    closed_at: str | None


class RecommendationService:
    def __init__(self, store: SQLiteMarketDataStore):
        self._store = store

    def save_strategy_text(self, strategy_text: str) -> dict[str, object]:
        return self._store.save_strategy_artifact(strategy_text=strategy_text)

    def list_strategy_artifacts(self, limit: int = 20) -> list[dict[str, object]]:
        return self._store.list_strategy_artifacts(limit=limit)

    def evaluate_lifecycle(self) -> int:
        open_rows = self._store.list_recommendations(query=None, include_suppressed=False)
        closed = 0
        for row in open_rows:
            if row.get("status") != "published":
                continue
            symbol = str(row["symbol"])
            latest_close = self._store.latest_close_for_symbol(symbol)
            if latest_close is None:
                continue
            direction = str(row["direction"])
            entry = float(row["entry_price"])
            spec = self._store.get_instrument_spec(symbol)
            lot_size = _resolve_lot_size(spec)
            pnl = (latest_close - entry) * lot_size if direction == "long" else (entry - latest_close) * lot_size
            reason: str | None = None
            if pnl >= 20000:
                reason = "profit_trigger"
            elif pnl <= -30000:
                reason = "loss_trigger"
            elif _is_cutoff_elapsed(str(row.get("created_at", "")), _resolve_expiry_date(spec)):
                reason = "cutoff_trigger"
            if reason is None:
                continue
            self._store.close_recommendation(
                recommendation_id=str(row["recommendation_id"]),
                close_reason=reason,
                close_price=latest_close,
                realized_pnl_per_lot=pnl,
            )
            closed += 1
        return closed

    def generate_from_signals(self) -> int:
        latest_strategy = self._store.latest_strategy_artifact()
        if latest_strategy is None:
            latest_strategy = self._store.save_strategy_artifact("Default momentum strategy baseline.")

        strategy_artifact_id = str(latest_strategy["artifact_id"])
        rows = self._store.list_recent_signals(limit=200)
        generated: list[dict[str, object]] = []
        for row in rows:
            confidence = float(row.get("fused_score", 0.0))
            symbol = str(row.get("symbol", "UNKNOWN"))
            signal_id = str(row.get("signal_id", ""))
            features = row.get("features", {}) if isinstance(row.get("features"), dict) else {}
            direction = "long" if confidence >= 0.5 else "short"
            support = float(row.get("support", 0.0))
            resistance = float(row.get("resistance", 0.0))
            entry_price = resistance if direction == "long" else support
            stop_loss = support if direction == "long" else resistance
            spread = abs(resistance - support)
            target_1 = entry_price + (spread * 1.35) if direction == "long" else entry_price - (spread * 1.35)
            target_2 = entry_price + (spread * 2.0) if direction == "long" else entry_price - (spread * 2.0)
            risk_per_unit = abs(entry_price - stop_loss) if abs(entry_price - stop_loss) > 0 else 0.0001
            reward_per_unit = abs(target_1 - entry_price)
            risk_reward_ratio = reward_per_unit / risk_per_unit
            spread_ratio = spread / entry_price if entry_price else 0.0
            volatility_regime = str(features.get("volatility_regime", "medium"))
            rationale = (
                f"Signal fusion={confidence:.2f}; breakout={row.get('breakout')}; "
                f"volume_spike={row.get('volume_spike')}; sentiment={row.get('sentiment_score')}; "
                f"rr={risk_reward_ratio:.2f}; volatility={volatility_regime}."
            )
            guardrail = self._guardrail_check(
                confidence=confidence,
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_1=target_1,
                rationale=rationale,
                risk_reward_ratio=risk_reward_ratio,
                spread_ratio=spread_ratio,
                volatility_regime=volatility_regime,
            )
            recommendation_id = _stable_recommendation_id(symbol=symbol, signal_id=signal_id, strategy_id=strategy_artifact_id)
            generated.append(
                {
                    "recommendation_id": recommendation_id,
                    "symbol": symbol,
                    "direction": direction,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "target_1": target_1,
                    "target_2": target_2,
                    "confidence": confidence,
                    "rationale": rationale,
                    "strategy_artifact_id": strategy_artifact_id,
                    "status": "published" if guardrail["ok"] else "suppressed",
                    "suppress_reason": None if guardrail["ok"] else guardrail["reason"],
                    "created_at": now_utc().isoformat(),
                    "close_reason": None,
                    "close_price": None,
                    "realized_pnl_per_lot": None,
                    "closed_at": None,
                    "signal_ids": [signal_id] if signal_id else [],
                }
            )
        return self._store.save_recommendations(generated)

    def list(self, query: str | None = None) -> list[Recommendation]:
        rows = self._store.list_recommendations(query=query, include_suppressed=False)
        return [self._to_dataclass(row) for row in rows]

    def get(self, recommendation_id: str) -> Recommendation | None:
        row = self._store.get_recommendation(recommendation_id)
        if row is None:
            return None
        return self._to_dataclass(row)

    @staticmethod
    def to_dict(item: Recommendation) -> dict[str, object]:
        return {
            "recommendation_id": item.recommendation_id,
            "symbol": item.symbol,
            "confidence": item.confidence,
            "direction": item.direction,
            "summary": item.summary,
            "tabs": item.tabs,
            "entry_price": item.entry_price,
            "stop_loss": item.stop_loss,
            "target_1": item.target_1,
            "target_2": item.target_2,
            "strategy_artifact_id": item.strategy_artifact_id,
            "signal_ids": item.signal_ids,
            "status": item.status,
            "suppress_reason": item.suppress_reason,
            "close_reason": item.close_reason,
            "close_price": item.close_price,
            "realized_pnl_per_lot": item.realized_pnl_per_lot,
            "closed_at": item.closed_at,
        }

    def _to_dataclass(self, row: dict[str, object]) -> Recommendation:
        symbol = str(row["symbol"])
        direction = str(row["direction"])
        confidence = float(row["confidence"])
        rationale = str(row["rationale"])
        return Recommendation(
            recommendation_id=str(row["recommendation_id"]),
            symbol=symbol,
            confidence=confidence,
            direction=direction,
            summary=rationale,
            tabs={
                "news": [f"Linked signals: {len(row.get('signal_ids', []))}"],
                "technicals": [f"Direction: {direction}", f"Confidence: {confidence:.2f}"],
                "strategy": [f"Strategy artifact: {row.get('strategy_artifact_id', '')}"],
            },
            entry_price=float(row["entry_price"]),
            stop_loss=float(row["stop_loss"]),
            target_1=float(row["target_1"]),
            target_2=float(row["target_2"]) if row.get("target_2") is not None else None,
            strategy_artifact_id=str(row["strategy_artifact_id"]),
            signal_ids=[str(item) for item in row.get("signal_ids", [])],
            status=str(row.get("status", "published")),
            suppress_reason=str(row["suppress_reason"]) if row.get("suppress_reason") else None,
            close_reason=str(row["close_reason"]) if row.get("close_reason") else None,
            close_price=float(row["close_price"]) if row.get("close_price") is not None else None,
            realized_pnl_per_lot=float(row["realized_pnl_per_lot"])
            if row.get("realized_pnl_per_lot") is not None
            else None,
            closed_at=str(row["closed_at"]) if row.get("closed_at") else None,
        )

    @staticmethod
    def _guardrail_check(
        confidence: float,
        entry_price: float,
        stop_loss: float,
        target_1: float,
        rationale: str,
        risk_reward_ratio: float,
        spread_ratio: float,
        volatility_regime: str,
    ) -> dict[str, object]:
        confidence_threshold = 0.35 if volatility_regime == "high" else 0.25
        if confidence < confidence_threshold:
            return {"ok": False, "reason": "confidence_below_threshold"}
        if not rationale.strip():
            return {"ok": False, "reason": "empty_rationale"}
        if entry_price <= 0 or stop_loss <= 0 or target_1 <= 0:
            return {"ok": False, "reason": "invalid_numeric_fields"}
        if spread_ratio < 0.002:
            return {"ok": False, "reason": "spread_too_narrow"}
        if risk_reward_ratio < 1.1:
            return {"ok": False, "reason": "risk_reward_below_threshold"}
        return {"ok": True}


def _stable_recommendation_id(symbol: str, signal_id: str, strategy_id: str) -> str:
    blob = f"{symbol}|{signal_id}|{strategy_id}".encode("utf-8")
    return f"rec-{hashlib.sha256(blob).hexdigest()[:16]}"


def now_utc() -> datetime:
    return datetime.now(UTC)


def _is_cutoff_elapsed(created_at: str, expiry_date: str | None) -> bool:
    now_ist = now_utc().astimezone(IST)
    if expiry_date:
        try:
            expiry_day = datetime.fromisoformat(expiry_date).date()
            cutoff_ist = datetime.combine(expiry_day, time(hour=15, minute=20), tzinfo=IST)
            return now_ist >= cutoff_ist
        except ValueError:
            pass
    if not created_at:
        return False
    try:
        ts = datetime.fromisoformat(created_at)
    except ValueError:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    inferred = _infer_monthly_expiry_cutoff(ts.astimezone(IST))
    if inferred is not None:
        return now_ist >= inferred
    return (now_utc() - ts).total_seconds() >= 24 * 3600


def _infer_monthly_expiry_cutoff(created_at_ist: datetime) -> datetime | None:
    try:
        year = created_at_ist.year
        month = created_at_ist.month
        first_cutoff = datetime.combine(_last_thursday(year, month), time(hour=15, minute=20), tzinfo=IST)
        if created_at_ist <= first_cutoff:
            return first_cutoff
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        second_cutoff = datetime.combine(_last_thursday(year, month), time(hour=15, minute=20), tzinfo=IST)
        return second_cutoff
    except Exception:
        return None


def _last_thursday(year: int, month: int) -> date:
    month_calendar = calendar.monthcalendar(year, month)
    thursdays = [week[calendar.THURSDAY] for week in month_calendar if week[calendar.THURSDAY] != 0]
    return date(year, month, thursdays[-1])


def _resolve_lot_size(spec: dict[str, object] | None) -> float:
    if not spec:
        return 1.0
    lot_size = spec.get("lot_size")
    if lot_size is None:
        return 1.0
    try:
        parsed = float(lot_size)
    except (TypeError, ValueError):
        return 1.0
    return parsed if parsed > 0 else 1.0


def _resolve_expiry_date(spec: dict[str, object] | None) -> str | None:
    if not spec:
        return None
    value = spec.get("expiry_date")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


IST = timezone(timedelta(hours=5, minutes=30))
