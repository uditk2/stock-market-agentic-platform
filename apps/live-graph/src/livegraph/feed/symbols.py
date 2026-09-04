"""Scrip-master parsing and trading-symbol to underlying mapping.

Kotak returns futures symbols like RELIANCE25SEPFUT. The graph is keyed on the
plain underlying (RELIANCE), so every tick has to be reduced to that root
before it can touch a graph node.
"""

from __future__ import annotations

import re
from datetime import datetime

from .models import Instrument, Segment

_FUT_ROOT_RE = re.compile(r"^([A-Z&\-]+?)(\d{2}[A-Z]{3})FUT$")
_OPT_ROOT_RE = re.compile(r"^([A-Z&\-]+?)(\d{2}[A-Z]{3})(\d+)(CE|PE)$")

_TOKEN_KEYS = ("pSymbol", "instrument_token", "token", "pToken")
_LABEL_KEYS = ("pTrdSymbol", "trading_symbol", "symbol", "pSymbolName")
_LOT_KEYS = ("lot_size", "lotsize", "lotSize", "pLotSize", "dLotSize")
_EXPIRY_KEYS = ("expiry_date", "expiry", "expiryDate", "pExpiryDate", "expDate")
_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%b-%Y", "%d%b%Y", "%d%b%y")


def extract_underlying(trading_symbol: str) -> str:
    """RELIANCE25SEPFUT -> RELIANCE. Returns the input unchanged for cash symbols."""
    label = trading_symbol.strip().upper()
    for pattern in (_FUT_ROOT_RE, _OPT_ROOT_RE):
        if match := pattern.match(label):
            return match.group(1)
    return label if label.isalpha() or "-" in label else ""


def is_futures_symbol(trading_symbol: str) -> bool:
    return _FUT_ROOT_RE.match(trading_symbol.strip().upper()) is not None


def parse_instruments(
    rows: list[dict[str, str]], segment: Segment, futures_only: bool = True
) -> list[Instrument]:
    """Turn scrip-master rows into Instruments, skipping anything unusable."""
    parsed = (_parse_row(row, segment, futures_only) for row in rows)
    return [item for item in parsed if item is not None]


def _parse_row(
    row: dict[str, str], segment: Segment, futures_only: bool
) -> Instrument | None:
    label = _first(row, _LABEL_KEYS).upper()
    token = _first(row, _TOKEN_KEYS)
    if not label or not token:
        return None
    if futures_only and segment is Segment.FNO and not is_futures_symbol(label):
        return None
    underlying = extract_underlying(label)
    if not underlying:
        return None
    return Instrument(
        instrument_token=token,
        segment=segment,
        trading_symbol=label,
        underlying=underlying,
        lot_size=_lot_size(row),
        expiry=_expiry(row),
    )


def nearest_expiry_per_underlying(instruments: list[Instrument]) -> list[Instrument]:
    """Keep one contract per underlying: the nearest dated expiry.

    Without this we would subscribe to every monthly series of every name and
    blow past the broker's subscription cap on redundant far-month contracts.
    """
    best: dict[str, Instrument] = {}
    for item in instruments:
        current = best.get(item.underlying)
        if current is None or _expiry_key(item) < _expiry_key(current):
            best[item.underlying] = item
    return sorted(best.values(), key=lambda i: i.underlying)


def _expiry_key(instrument: Instrument) -> str:
    #: Undated contracts sort last so a dated one always wins.
    return instrument.expiry or "9999-12-31"


def _first(row: dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = row.get(key)
        if value and str(value).strip():
            return str(value).strip()
    return ""


def _lot_size(row: dict[str, str]) -> int | None:
    raw = _first(row, _LOT_KEYS).replace(",", "")
    try:
        parsed = int(float(raw))
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _expiry(row: dict[str, str]) -> str | None:
    raw = _first(row, _EXPIRY_KEYS)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None
