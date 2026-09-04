"""Assemble the movers scan and the per-stock drill-down.

This is the composite layer: it reads the graph, the live feed and the news
store and produces what the UI walks through. The pieces it composes stay
independent; only this module knows about all three.
"""

from __future__ import annotations

from collections.abc import Callable

from ..feed import Tick
from ..graph import EdgeType, GraphRepository, NodeType
from ..news import NewsItem
from . import scoping, verdict as verdict_rules
from .websearch import WebNewsSearch
from .models import (
    GraphDriver,
    NewsScope,
    MoverRow,
    PeerMove,
    ScopedNews,
    SectorContext,
    StockScan,
    VERDICT_RANK,
    Verdict,
)

DEFAULT_MOVERS_PER_SIDE = 10


class ScanService:
    def __init__(
        self,
        repo: GraphRepository,
        ticks: Callable[[], dict[str, Tick]],
        news_for: Callable[[str], list[NewsItem]],
        recent_news: Callable[[int], list[NewsItem]],
        web_search: WebNewsSearch | None = None,
    ):
        self._repo = repo
        self._ticks = ticks
        self._news_for = news_for
        self._recent_news = recent_news
        self._web = web_search

    # ---- the scan ----------------------------------------------------

    def movers(self, per_side: int = DEFAULT_MOVERS_PER_SIDE) -> tuple[list[MoverRow], list[MoverRow]]:
        """Biggest movers each way, each already carrying its verdict."""
        priced = self._priced()
        gainers = sorted((s for s, v in priced.items() if v > 0), key=lambda s: -priced[s])
        losers = sorted((s for s, v in priced.items() if v < 0), key=lambda s: priced[s])
        return (
            [self._mover_row(s) for s in gainers[:per_side]],
            [self._mover_row(s) for s in losers[:per_side]],
        )

    def _mover_row(self, symbol: str) -> MoverRow:
        node = self._repo.require(symbol)
        tick = self._ticks()[symbol]
        return MoverRow(
            symbol=symbol,
            name=node.name,
            sector=node.sector,
            ltp=tick.ltp,
            change_pct=tick.change_pct or 0.0,
            verdict=self._verdict_only(symbol),
        )

    def _verdict_only(self, symbol: str) -> Verdict:
        """Cheap path for list rows: no news bodies, only their counts."""
        moves = self._priced()
        evidence = verdict_rules.build_evidence(
            change_pct=moves.get(symbol, 0.0),
            peers=self.peers_of(symbol),
            sector=self.sector_context(symbol),
            drivers=self.drivers_of(symbol),
            news_counts=self._news_counts(symbol),
        )
        return verdict_rules.classify(evidence)

    # ---- the drill-down ----------------------------------------------

    def stock(self, symbol: str, search_web: bool = False) -> StockScan:
        key = symbol.strip().upper()
        node = self._repo.require(key)
        moves = self._priced()
        tick = self._ticks().get(key)

        peers = self.peers_of(key)
        sector = self.sector_context(key)
        drivers = self.drivers_of(key)
        news = self.news_of(key)
        if search_web:
            news = self._with_web_fallback(news, key, node.name, node.sector)

        evidence = verdict_rules.build_evidence(
            change_pct=moves.get(key, 0.0),
            peers=peers,
            sector=sector,
            drivers=drivers,
            news_counts=verdict_rules.news_counts([n.scope for n in news]),
        )
        return StockScan(
            symbol=key,
            name=node.name,
            sector=node.sector,
            peer_groups=node.peer_groups,
            ltp=tick.ltp if tick else 0.0,
            change_pct=moves.get(key, 0.0),
            verdict=verdict_rules.classify(evidence),
            evidence=evidence,
            peers=tuple(peers),
            drivers=tuple(drivers),
            news=tuple(news),
        )

    def explain(self, scan: StockScan) -> str:
        return verdict_rules.explain(scan.symbol, scan.evidence, scan.verdict)

    # ---- components --------------------------------------------------

    def peers_of(self, symbol: str) -> list[PeerMove]:
        """Priced peers only; an unpriced peer is absent, never a zero."""
        moves = self._priced()
        return [
            PeerMove(symbol=peer, change_pct=moves[peer])
            for peer in self._repo.peers_of(symbol)
            if peer in moves
        ]

    def sector_context(self, symbol: str) -> SectorContext | None:
        node = self._repo.get(symbol)
        if node is None or not node.sector:
            return None
        moves = self._priced()
        member_moves = [moves[m] for m in self._repo.sector_members(node.sector) if m in moves]
        if not member_moves:
            return None
        return SectorContext(
            name=node.sector,
            avg_change_pct=sum(member_moves) / len(member_moves),
            advancing=sum(1 for v in member_moves if v > 0),
            declining=sum(1 for v in member_moves if v < 0),
        )

    def drivers_of(self, symbol: str) -> list[GraphDriver]:
        """Typed edges into this stock, with the driver's own move when priced."""
        moves = self._priced()
        drivers: list[GraphDriver] = []
        for neighbour in self._repo.neighbours(symbol):
            edge = neighbour.edge
            if edge.type in (EdgeType.IN_SECTOR, EdgeType.PEER_OF):
                continue
            drivers.append(
                GraphDriver(
                    edge_type=str(edge.type),
                    node=neighbour.node.id,
                    sign=edge.sign,
                    strength=edge.strength,
                    note=edge.note,
                    driver_change_pct=moves.get(neighbour.node.id),
                )
            )
        drivers.sort(key=lambda d: -d.strength)
        return drivers

    def news_of(self, symbol: str) -> list[ScopedNews]:
        node = self._repo.get(symbol)
        members = set(self._repo.sector_members(node.sector)) if node and node.sector else set()
        #: Tagged items for this symbol, plus a slice of the wider feed so
        #: sector and market context can be found at all.
        pool = {item.link: item for item in self._news_for(symbol)}
        for item in self._recent_news(120):
            pool.setdefault(item.link, item)
        return scoping.collect(
            items=list(pool.values()),
            symbol=symbol,
            sector_members=members | {symbol},
            is_macro=self._is_macro,
        )

    def _with_web_fallback(
        self, news: list[ScopedNews], symbol: str, name: str, sector: str | None
    ) -> list[ScopedNews]:
        """Search the web only when nothing is tagged to the stock itself.

        A sector headline is context, not an explanation for one name standing
        apart, so its presence does not count as coverage here.
        """
        if self._web is None or not self._web.is_configured():
            return news
        if any(item.scope is NewsScope.STOCK for item in news):
            return news
        return self._web.search(symbol, name, sector) + news

    def sector_rows(self, sector: str) -> list[MoverRow]:
        """Every priced member of a sector, strongest first."""
        moves = self._priced()
        members = [m for m in self._repo.sector_members(sector) if m in moves]
        members.sort(key=lambda s: -moves[s])
        return [self._mover_row(s) for s in members]

    def rank(self, rows: list[MoverRow]) -> list[MoverRow]:
        return sorted(rows, key=lambda r: (VERDICT_RANK[r.verdict], -abs(r.change_pct)))

    # ---- helpers -----------------------------------------------------

    def _priced(self) -> dict[str, float]:
        return {
            symbol: tick.change_pct
            for symbol, tick in self._ticks().items()
            if tick.change_pct is not None
        }

    def _news_counts(self, symbol: str) -> dict[str, int]:
        """Counts without scoping the whole feed, for list rows."""
        stock_items = self._news_for(symbol)
        return {"stock": len(stock_items)} if stock_items else {}

    def _is_macro(self, node_id: str) -> bool:
        node = self._repo.get(node_id)
        return node is not None and node.type is NodeType.MACRO
