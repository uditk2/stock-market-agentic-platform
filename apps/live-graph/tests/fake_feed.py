"""A tick source for tests.

Lives in the test suite on purpose. The application has no synthetic feed: one
that invents prices can be mistaken for the market, so it is not something the
product should be able to start with by accident.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable

from livegraph.feed import Segment, Tick


class FakeFeed:
    """Emits a fixed set of moves. Deterministic, and never starts a thread."""

    def __init__(self, moves: Iterable[tuple[str, float, float]]):
        self._ticks = {
            symbol: Tick(
                underlying=symbol, segment=Segment.FNO, trading_symbol=f"{symbol}-TEST",
                ltp=ltp, change_pct=change, open_interest=None, volume=None, ts=time.time(),
            )
            for symbol, ltp, change in moves
        }
        self._handlers: list[Callable[[Tick], None]] = []
        self._lock = threading.Lock()
        self.started = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def add_handler(self, handler) -> None:
        self._handlers.append(handler)

    def remove_handler(self, handler) -> None:
        if handler in self._handlers:
            self._handlers.remove(handler)

    def emit(self, symbol: str, ltp: float, change_pct: float) -> None:
        """Push one tick, as the real socket would."""
        tick = Tick(
            underlying=symbol, segment=Segment.FNO, trading_symbol=f"{symbol}-TEST",
            ltp=ltp, change_pct=change_pct, open_interest=None, volume=None, ts=time.time(),
        )
        with self._lock:
            self._ticks[symbol] = tick
        for handler in list(self._handlers):
            handler(tick)

    @property
    def is_connected(self) -> bool:
        return self.started

    @property
    def instrument_count(self) -> int:
        return len(self._ticks)

    def latest(self, underlying: str) -> Tick | None:
        with self._lock:
            return self._ticks.get(underlying)

    def snapshot(self, segment: Segment | None = None) -> dict[str, Tick]:
        with self._lock:
            return dict(self._ticks)
