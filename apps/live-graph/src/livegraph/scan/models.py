"""Shapes for the movers scan and the stock drill-down."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Verdict(StrEnum):
    """Why a move looks the way it does. Ordered by how much attention it wants."""

    UNEXPLAINED = "unexplained"
    CONFLICTED = "conflicted"
    STOCK_SPECIFIC = "stock_specific"
    SECTOR_WIDE = "sector_wide"


#: Sort order for the scan: the odd ones first, the ordinary last.
VERDICT_RANK: dict[Verdict, int] = {
    Verdict.UNEXPLAINED: 0,
    Verdict.CONFLICTED: 1,
    Verdict.STOCK_SPECIFIC: 2,
    Verdict.SECTOR_WIDE: 3,
}

VERDICT_LABEL: dict[Verdict, str] = {
    Verdict.UNEXPLAINED: "Unexplained",
    Verdict.CONFLICTED: "Conflicted",
    Verdict.STOCK_SPECIFIC: "Stock-specific",
    Verdict.SECTOR_WIDE: "Sector-wide",
}


class NewsScope(StrEnum):
    STOCK = "stock"
    SECTOR = "sector"
    MARKET = "market"
    WEB = "web"


@dataclass(frozen=True, slots=True)
class PeerMove:
    symbol: str
    change_pct: float


@dataclass(frozen=True, slots=True)
class SectorContext:
    name: str
    avg_change_pct: float
    advancing: int
    declining: int

    @property
    def breadth(self) -> int:
        return self.advancing + self.declining

    @property
    def is_one_sided(self) -> bool:
        """A sector where nearly everything moves the same way explains its members."""
        if self.breadth < 3:
            return False
        dominant = max(self.advancing, self.declining)
        return dominant / self.breadth >= 0.8


@dataclass(frozen=True, slots=True)
class GraphDriver:
    """A typed edge, with the driver's own move where one is known."""

    edge_type: str
    node: str
    sign: int
    strength: float
    note: str | None = None
    driver_change_pct: float | None = None

    @property
    def expected_direction(self) -> int:
        """Which way this driver should push the stock, or 0 if the driver is flat."""
        if self.driver_change_pct is None or self.sign == 0:
            return 0
        moved = 1 if self.driver_change_pct > 0 else -1
        return moved * self.sign


@dataclass(frozen=True, slots=True)
class ScopedNews:
    scope: NewsScope
    title: str
    source: str
    ts: float
    link: str = ""
    #: Which graph node the resolver matched, when it was a tagged headline.
    matched_node: str | None = None


@dataclass(frozen=True, slots=True)
class Evidence:
    """Everything the verdict was computed from, so it can be checked."""

    change_pct: float
    peer_avg: float | None
    peer_count: int
    gap: float | None
    sector: SectorContext | None
    #: Gap in standard deviations of the peer moves. None when the peers are
    #: too few, or so tightly clustered that dividing by the spread is noise.
    peer_z: float | None = None
    news_counts: dict[str, int] = field(default_factory=dict)
    conflicting_drivers: tuple[GraphDriver, ...] = ()

    @property
    def has_news(self) -> bool:
        return any(self.news_counts.get(s, 0) for s in ("stock", "web"))


@dataclass(frozen=True, slots=True)
class MoverRow:
    symbol: str
    name: str
    sector: str | None
    ltp: float
    change_pct: float
    verdict: Verdict


@dataclass(frozen=True, slots=True)
class StockScan:
    symbol: str
    name: str
    sector: str | None
    peer_groups: tuple[str, ...]
    ltp: float
    change_pct: float
    verdict: Verdict
    evidence: Evidence
    peers: tuple[PeerMove, ...]
    drivers: tuple[GraphDriver, ...]
    news: tuple[ScopedNews, ...]
