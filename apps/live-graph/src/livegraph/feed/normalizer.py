"""Turn raw Kotak WebSocket payloads into Ticks.

Kotak sends compact keys over the socket (`tk`, `ts`, `ltp`, `nc`, `oi`, `ft`)
but the REST quote endpoints use long ones. Both shapes are accepted here so a
change of transport does not ripple outward.
"""

from __future__ import annotations

import time
from typing import Any

from .models import Instrument, Segment, Tick

#: `c` and `close` are deliberately absent. In Kotak's socket protocol they are
#: the *previous day's* close, not the last price, so a partial frame carrying
#: `c` without `ltp` would have been read as a live price and published a stale
#: one. The REST spellings that do mean last price are listed instead.
_LTP_KEYS = ("ltp", "last_traded_price", "lp", "last_price")
_PREV_CLOSE_KEYS = ("c", "close", "prev_day_close", "ic")
_OPEN_KEYS = ("op", "open", "openingPrice")
_CHANGE_PCT_KEYS = ("nc", "change_percent", "pc", "chgp")
_OI_KEYS = ("oi", "open_interest", "opnInterest")
_VOLUME_KEYS = ("v", "volume", "vol", "ltq")
_TOKEN_KEYS = ("tk", "instrument_token", "token")
_SYMBOL_KEYS = ("ts", "trading_symbol", "tradingSymbol", "symbol")
_SEGMENT_KEYS = ("e", "exchange_segment", "segment")
_TIME_KEYS = ("ft", "feed_time", "ltt", "timestamp")

#: Kotak does not send a bare quote. It sends an envelope — `{"type": "...",
#: "data": [...]}` — and the quotes are inside `data`. The envelope carries no
#: price of its own, so parsing it directly yields nothing at all.
_ENVELOPE_KEYS = ("data", "d", "payload", "message")

#: A frame nested deeper than this is not a shape worth chasing.
_MAX_ENVELOPE_DEPTH = 4


class TickNormalizer:
    """Maps raw socket payloads to Ticks using a token -> Instrument index."""

    def __init__(self, instruments: dict[str, Instrument]):
        self._by_token = instruments

    def normalize_message(self, message: Any) -> list[Tick]:
        """A socket message may carry one quote, many, or an envelope of them."""
        ticks = (self.normalize_one(p) for p in quote_payloads(message))
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
            prev_close=_as_float(_first(payload, _PREV_CLOSE_KEYS)),
            day_open=_as_float(_first(payload, _OPEN_KEYS)),
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


def quote_payloads(message: Any, depth: int = 0) -> list[dict[str, Any]]:
    """Flatten a socket message down to the quote dicts inside it.

    A dict is treated as an envelope only when it holds no price itself, so a
    quote that happens to carry one of these keys is never unwrapped past the
    data it came to deliver.
    """
    if depth > _MAX_ENVELOPE_DEPTH:
        return []
    if isinstance(message, list):
        return [p for item in message for p in quote_payloads(item, depth + 1)]
    if not isinstance(message, dict):
        return []
    inner = _first(message, _ENVELOPE_KEYS)
    if inner is not None and _first(message, _LTP_KEYS) is None:
        return quote_payloads(inner, depth + 1)
    return [message]


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
