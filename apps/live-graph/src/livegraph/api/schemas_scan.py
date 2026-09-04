"""Response shapes for the movers scan and drill-down."""

from __future__ import annotations

from pydantic import BaseModel


class MoverOut(BaseModel):
    symbol: str
    name: str
    sector: str | None = None
    ltp: float
    change_pct: float
    verdict: str
    verdict_label: str


class MoversOut(BaseModel):
    gainers: list[MoverOut]
    losers: list[MoverOut]
    #: Repeated here so the UI does not need a second call to label the strip.
    sectors: list[dict]


class PeerOut(BaseModel):
    symbol: str
    change_pct: float
    vs_peer_avg: float


class SectorOut(BaseModel):
    name: str
    avg_change_pct: float
    advancing: int
    declining: int
    breadth: int
    one_sided: bool


class DriverOut(BaseModel):
    edge_type: str
    node: str
    sign: int
    strength: float
    note: str | None = None
    driver_change_pct: float | None = None
    expected_direction: int
    conflicting: bool = False


class NewsOut(BaseModel):
    scope: str
    title: str
    source: str
    ts: float
    link: str = ""
    matched_node: str | None = None


class EvidenceOut(BaseModel):
    change_pct: float
    peer_avg: float | None = None
    peer_count: int
    gap: float | None = None
    news_counts: dict[str, int] = {}


class StockScanOut(BaseModel):
    symbol: str
    name: str
    sector: str | None = None
    peer_groups: list[str] = []
    ltp: float
    change_pct: float
    verdict: str
    verdict_label: str
    why: str
    evidence: EvidenceOut
    sector_context: SectorOut | None = None
    peers: list[PeerOut] = []
    drivers: list[DriverOut] = []
    news: list[NewsOut] = []
    narration: NarrationOut | None = None


class NarrationOut(BaseModel):
    text: str
    written_at: float
    from_cache: bool
    refreshed_because: str | None = None


class SectorDetailOut(BaseModel):
    sector: SectorOut
    members: list[MoverOut]
