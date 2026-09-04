"""A synthetic tick source for development.

Exists so the API and UI can be built and verified without live credentials or
an open market. It is always reported to the client as mode="simulated" so a
simulated price can never be mistaken for a real one.

Moves are correlated inside a peer group and then again inside a sector, which
is what makes divergence and co-movement visibly exercisable offline.
"""

from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable, Iterable

from .models import Segment, Tick

DEFAULT_INTERVAL_SECONDS = 2.0
_SECTOR_BETA = 0.55
_PEER_BETA = 0.30
_IDIOSYNCRATIC = 0.15
_TICK_SCALE = 0.35
#: Pull back toward zero each step. Without it the walk drifts to the clamp and
#: sticks there, so after a few minutes every symbol reads exactly +/-9% and the
#: divergence scan has nothing left to distinguish.
_MEAN_REVERSION = 0.04
_CLAMP_PCT = 9.0
#: Occasional single-stock shocks, standing in for company-specific news.
#: Without them every large move is a whole sector moving together, the peer
#: gap is always small, and the scan can only ever return "sector-wide" - which
#: makes a working classifier look broken.
_SHOCK_PROBABILITY = 0.004
_SHOCK_SIZE = 2.2


class SimulatedFeed:
    """Random walk with sector and peer-group common factors."""

    def __init__(
        self,
        symbols: Iterable[str],
        sectors: dict[str, str],
        peer_groups: dict[str, str],
        interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
        seed: int = 7,
    ):
        self._symbols = list(symbols)
        self._sectors = sectors
        self._peer_groups = peer_groups
        self._interval = interval_seconds
        self._random = random.Random(seed)
        self._base = {s: self._random.uniform(120.0, 3800.0) for s in self._symbols}
        self._change = {s: 0.0 for s in self._symbols}
        self._handlers: list[Callable[[Tick], None]] = []
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._latest: dict[str, Tick] = {}

    # ---- lifecycle ---------------------------------------------------

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="simulated-feed")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread = None

    def _loop(self) -> None:
        while not self._stop.wait(self._interval):
            for tick in self._step():
                for handler in list(self._handlers):
                    handler(tick)

    def _step(self) -> list[Tick]:
        """Advance every symbol one step and record the result.

        Recording happens here rather than in the loop so the simulator can be
        stepped directly in a test without starting a thread.
        """
        sector_shock = self._shocks(set(self._sectors.values()))
        peer_shock = self._shocks(set(self._peer_groups.values()))
        now = time.time()
        ticks = [self._tick(symbol, sector_shock, peer_shock, now) for symbol in self._symbols]
        with self._lock:
            for tick in ticks:
                self._latest[tick.underlying] = tick
        return ticks

    def _shocks(self, keys: set[str]) -> dict[str, float]:
        return {key: self._random.gauss(0.0, 1.0) for key in keys}

    def _tick(
        self, symbol: str, sector_shock: dict[str, float], peer_shock: dict[str, float], now: float
    ) -> Tick:
        move = (
            _SECTOR_BETA * sector_shock.get(self._sectors.get(symbol, ""), 0.0)
            + _PEER_BETA * peer_shock.get(self._peer_groups.get(symbol, ""), 0.0)
            + _IDIOSYNCRATIC * self._random.gauss(0.0, 1.0)
        ) * _TICK_SCALE
        if self._random.random() < _SHOCK_PROBABILITY:
            move += self._random.choice((-1, 1)) * _SHOCK_SIZE
        #: Ornstein-Uhlenbeck style: accumulate, but pull back toward zero so the
        #: series stays in a plausible band instead of parking on the clamp.
        previous = self._change[symbol]
        updated = previous + move - _MEAN_REVERSION * previous
        self._change[symbol] = max(-_CLAMP_PCT, min(_CLAMP_PCT, updated))
        change = self._change[symbol]
        return Tick(
            underlying=symbol,
            segment=Segment.FNO,
            trading_symbol=f"{symbol}-SIM",
            ltp=round(self._base[symbol] * (1 + change / 100), 2),
            change_pct=round(change, 2),
            open_interest=None,
            volume=None,
            ts=now,
        )

    # ---- parity with TickStream --------------------------------------

    def add_handler(self, handler: Callable[[Tick], None]) -> None:
        self._handlers.append(handler)

    def remove_handler(self, handler: Callable[[Tick], None]) -> None:
        if handler in self._handlers:
            self._handlers.remove(handler)

    @property
    def is_connected(self) -> bool:
        return self._thread is not None and not self._stop.is_set()

    @property
    def instrument_count(self) -> int:
        return len(self._symbols)

    def latest(self, underlying: str) -> Tick | None:
        with self._lock:
            return self._latest.get(underlying)

    def snapshot(self, segment: Segment | None = None) -> dict[str, Tick]:
        with self._lock:
            return dict(self._latest)
