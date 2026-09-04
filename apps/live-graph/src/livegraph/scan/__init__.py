"""Movers scan and per-stock drill-down. Joins graph, feed and news."""

from .models import (
    Evidence,
    GraphDriver,
    MoverRow,
    NewsScope,
    PeerMove,
    ScopedNews,
    SectorContext,
    StockScan,
    VERDICT_LABEL,
    VERDICT_RANK,
    Verdict,
)
from .service import ScanService
from .verdict import build_evidence, classify, explain

__all__ = [
    "Evidence",
    "GraphDriver",
    "MoverRow",
    "NewsScope",
    "PeerMove",
    "ScanService",
    "ScopedNews",
    "SectorContext",
    "StockScan",
    "VERDICT_LABEL",
    "VERDICT_RANK",
    "Verdict",
    "build_evidence",
    "classify",
    "explain",
]
