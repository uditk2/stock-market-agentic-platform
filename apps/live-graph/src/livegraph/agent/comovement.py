"""Spot stocks that move together but have no edge between them.

Correlation is evidence for a candidate edge, never proof of one. Intraday
co-movement is driven by index flows and shared beta as much as by any real
supply or competitive link, so everything here is a proposal for a human to
accept or reject, and the sample count is always reported alongside it.
"""

from __future__ import annotations

import statistics
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

#: Below this many observations a correlation is not worth reporting.
MIN_SAMPLES = 30
DEFAULT_WINDOW = 240
DEFAULT_MIN_CORRELATION = 0.85


@dataclass(frozen=True, slots=True)
class EdgeProposal:
    source: str
    target: str
    correlation: float
    samples: int
    #: Set when both stocks already sit in the same sector, which makes shared
    #: index flow the likelier explanation than a specific relationship.
    same_sector: bool = False

    @property
    def confidence(self) -> str:
        if self.samples < MIN_SAMPLES * 2 or self.same_sector:
            return "low"
        return "moderate" if self.correlation < 0.93 else "high"


@dataclass
class PriceHistory:
    """Rolling per-symbol series of percentage moves."""

    window: int = DEFAULT_WINDOW
    _series: dict[str, deque[float]] = field(default_factory=dict)

    def record(self, symbol: str, change_pct: float) -> None:
        series = self._series.get(symbol)
        if series is None:
            series = deque(maxlen=self.window)
            self._series[symbol] = series
        series.append(change_pct)

    def series(self, symbol: str) -> list[float]:
        return list(self._series.get(symbol, ()))

    def symbols(self) -> list[str]:
        return sorted(self._series)

    def sample_count(self, symbol: str) -> int:
        return len(self._series.get(symbol, ()))


class CoMovementAnalyzer:
    def __init__(
        self,
        history: PriceHistory,
        min_correlation: float = DEFAULT_MIN_CORRELATION,
        min_samples: int = MIN_SAMPLES,
    ):
        self._history = history
        self._min_correlation = min_correlation
        self._min_samples = min_samples

    def propose(
        self,
        has_edge: Callable[[str, str], bool],
        same_sector: Callable[[str, str], bool],
        limit: int = 20,
    ) -> list[EdgeProposal]:
        """Correlated pairs the graph does not already connect."""
        symbols = [
            s for s in self._history.symbols()
            if self._history.sample_count(s) >= self._min_samples
        ]
        proposals = [
            proposal
            for index, left in enumerate(symbols)
            for right in symbols[index + 1:]
            if not has_edge(left, right)
            and (proposal := self._score(left, right, same_sector)) is not None
        ]
        proposals.sort(key=lambda p: -p.correlation)
        return proposals[:limit]

    def _score(
        self, left: str, right: str, same_sector: Callable[[str, str], bool]
    ) -> EdgeProposal | None:
        a, b = self._aligned(left, right)
        if len(a) < self._min_samples:
            return None
        correlation = _pearson(a, b)
        if correlation is None or correlation < self._min_correlation:
            return None
        return EdgeProposal(
            source=left,
            target=right,
            correlation=round(correlation, 4),
            samples=len(a),
            same_sector=same_sector(left, right),
        )

    def _aligned(self, left: str, right: str) -> tuple[list[float], list[float]]:
        """Compare the same number of observations from each series.

        Symbols start streaming at different times, so the series are trimmed to
        their common tail rather than zero-padded, which would invent data.
        """
        a, b = self._history.series(left), self._history.series(right)
        size = min(len(a), len(b))
        return a[-size:], b[-size:]


def _pearson(a: list[float], b: list[float]) -> float | None:
    """None when either series is flat, where correlation is undefined."""
    try:
        return statistics.correlation(a, b)
    except statistics.StatisticsError:
        return None
