"""Turn raw Kotak WebSocket payloads into Ticks.

Kotak sends compact keys over the socket (`tk`, `ts`, `ltp`, `nc`, `oi`, `ft`)
but the REST quote endpoints use long ones. Both shapes are accepted here so a
change of transport does not ripple outward.
"""

from __future__ import annotations

import time
from typing import Any

from .models import Instrument, Segment, Tick

_LTP_KEYS = ("ltp", "last_traded_price", "lp", "c", "close")
_CHANGE_PCT_KEYS = ("nc", "change_percent", "pc", "chgp")
_OI_KEYS = ("oi", "open_interest", "opnInterest")
_VOLUME_KEYS = ("v", "volume", "vol", "ltq")
_TOKEN_KEYS = ("tk", "instrument_token", "token")
_SYMBOL_KEYS = ("ts", "trading_symbol", "tradingSymbol", "symbol")
_SEGMENT_KEYS = ("e", "exchange_segment", "segment")
_TIME_KEYS = ("ft", "feed_time", "ltt", "timestamp")


class TickNormalizer:
    """Maps raw socket payloads to Ticks using a token -> Instrument index."""

    def __init__(self, instruments: dict[str, Instrument]):
        self._by_token = instruments

    def normalize_message(self, message: Any) -> list[Tick]:
        """A single socket message may carry one or many quote dicts."""
        payloads = message if isinstance(message, list) else [message]
        ticks = (self.normalize_one(p) for p in payloads if isinstance(p, dict))
        return [tick for tick in ticks if tick is not None]

    def normalize_one(self, payload: dict[str, Any]) -> Tick | None:
        instrument = self._resolve(payload)
        if instrument is None:
            return None
        ltp = _as_float(_first(payload, _LTP_KEYS))
        if ltp is None:
            #: Depth-only or heartbeat frames carry no price; nothing to emit.
            return None
        return Tick(
            underlying=instrument.underlying,
            segment=instrument.segment,
            trading_symbol=instrument.trading_symbol,
            ltp=ltp,
            change_pct=_as_float(_first(payload, _CHANGE_PCT_KEYS)),
            open_interest=_as_int(_first(payload, _OI_KEYS)),
            volume=_as_int(_first(payload, _VOLUME_KEYS)),
            ts=_as_float(_first(payload, _TIME_KEYS)) or time.time(),
        )

    def _resolve(self, payload: dict[str, Any]) -> Instrument | None:
        """Prefer the token index; fall back to the symbol carried in the frame."""
        token = _as_text(_first(payload, _TOKEN_KEYS))
        if token and (instrument := self._by_token.get(token)) is not None:
            return instrument
        symbol = _as_text(_first(payload, _SYMBOL_KEYS)).upper()
        if not symbol:
            return None
        return next(
            (i for i in self._by_token.values() if i.trading_symbol == symbol), None
        )


def parse_segment(value: str) -> Segment | None:
    try:
        return Segment(value.strip().lower())
    except ValueError:
        return None


def _first(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if (value := payload.get(key)) not in (None, ""):
            return value
    return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    parsed = _as_float(value)
    return int(parsed) if parsed is not None else None


def _as_text(value: Any) -> str:
    return "" if value is None else str(value).strip()
