from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Segment(StrEnum):
    """Kotak exchange segments. We only ever subscribe to these two."""

    CASH = "nse_cm"
    FNO = "nse_fo"


@dataclass(frozen=True, slots=True)
class Instrument:
    """One subscribable contract, already mapped back to its graph node."""

    instrument_token: str
    segment: Segment
    trading_symbol: str
    #: Underlying root, e.g. RELIANCE. This is the graph node id.
    underlying: str
    lot_size: int | None = None
    expiry: str | None = None

    def as_subscription(self) -> dict[str, str]:
        return {
            "instrument_token": self.instrument_token,
            "exchange_segment": str(self.segment),
        }


@dataclass(frozen=True, slots=True)
class Tick:
    """A normalised price update. The only thing `feed` emits outward."""

    underlying: str
    segment: Segment
    trading_symbol: str
    ltp: float
    change_pct: float | None
    open_interest: int | None
    volume: int | None
    ts: float

    @property
    def is_futures(self) -> bool:
        return self.segment is Segment.FNO
