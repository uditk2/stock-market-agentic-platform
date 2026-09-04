"""The single place feed, graph and news are joined.

Those three modules never import one another; everything that needs more than
one of them goes through AppState.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from ..agent import AnalystDeps, AnalystService, CoMovementAnalyzer, PriceHistory
from ..feed import KotakSession, KotakSettings, Segment, Tick
from ..feed.simulator import SimulatedFeed
from ..graph import GraphRepository, NodeType
from ..paths import data_dir as resolve_data_dir
from ..news import EntityResolver, NewsItem, NewsPoller
from ..scan import ScanService
from ..scan.narrator import VerdictNarrator
from ..scan.websearch import WebNewsSearch
from ..scratchpad import MarketSnapshot, PyodideSandbox

logger = logging.getLogger(__name__)

#: How often a symbol's move is folded into the co-movement history.
HISTORY_INTERVAL_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class FeedStatus:
    mode: str
    connected: bool
    instruments: int
    symbols_priced: int
    detail: str = ""


class AppState:
    def __init__(self, data_dir: Path | None = None, simulate: bool = False):
        resolved = data_dir or resolve_data_dir()
        self.repo = GraphRepository.from_file(resolved / "stock_graph.json")
        self.history = PriceHistory()
        self.comovement = CoMovementAnalyzer(self.history)
        self.sandbox = PyodideSandbox()
        self.news = self._build_news(resolved)
        self.feed, self.feed_mode, self.feed_detail = self._build_feed(simulate)
        self.kotak_session: "KotakSession | None" = None
        self._last_history_write = 0.0
        self._subscribers: list = []
        self._lock = threading.Lock()
        self.analyst = AnalystService(self._analyst_deps())
        self.scan = ScanService(
            repo=self.repo,
            ticks=self.ticks,
            news_for=lambda symbol: self.news.for_node(symbol, limit=10),
            recent_news=lambda limit: self.news.recent(limit=limit),
            web_search=WebNewsSearch(),
        )
        self.narrator = VerdictNarrator()
        self.feed.add_handler(self._on_tick)

    # ---- construction ------------------------------------------------

    def _build_news(self, data_dir: Path) -> NewsPoller:
        stocks = self.repo.nodes_of_type(NodeType.STOCK)
        known = frozenset(n.id for n in stocks) | frozenset(
            n.id for n in self.repo.nodes_of_type(NodeType.MACRO)
        )
        resolver = EntityResolver.from_file(
            data_dir / "aliases.json", {n.id: n.name for n in stocks}, known
        )
        return NewsPoller(
            resolver=resolver,
            is_fo=lambda node_id: bool((n := self.repo.get(node_id)) and n.fo),
        )

    def _build_feed(self, simulate: bool):
        """Live Kotak when credentials are present, otherwise the simulator.

        The mode is surfaced to the client so a simulated price is never shown
        as a real one.
        """
        settings = KotakSettings()
        if simulate or not settings.is_configured:
            missing = ", ".join(settings.missing_fields())
            detail = (
                "simulator requested"
                if simulate
                else f"Kotak credentials incomplete: {missing}"
            )
            logger.warning("Using simulated feed (%s)", detail)
            return self._simulated_feed(), "simulated", detail
        return self._live_feed(settings)

    def _simulated_feed(self) -> SimulatedFeed:
        stocks = [n for n in self.repo.nodes_of_type(NodeType.STOCK) if n.fo]
        return SimulatedFeed(
            symbols=[n.id for n in stocks],
            sectors={n.id: n.sector or "Unknown" for n in stocks},
            peer_groups={
                n.id: (n.peer_groups[0] if n.peer_groups else "NONE") for n in stocks
            },
        )

    def _live_feed(self, settings: KotakSettings):
        from ..feed import KotakSession, TickStream, nearest_expiry_per_underlying, parse_instruments

        session = KotakSession(settings)
        self.kotak_session = session
        client = session.login()
        rows = client.scrip_master(exchange_segment=str(Segment.FNO))
        instruments = nearest_expiry_per_underlying(parse_instruments(rows, Segment.FNO))
        tradable = {n.id for n in self.repo.nodes_of_type(NodeType.STOCK)}
        selected = [i for i in instruments if i.underlying in tradable]
        stream = TickStream(client, selected)
        return stream, "live", f"{len(selected)} contracts"

    def _analyst_deps(self) -> AnalystDeps:
        return AnalystDeps(
            repo=self.repo,
            comovement=self.comovement,
            moves=self.moves,
            prices=self.prices,
            news_for=lambda symbol: self.news.for_node(symbol),
        )

    # ---- lifecycle ---------------------------------------------------

    def start(self) -> None:
        self.feed.start()
        self._start_sandbox()

    def _start_sandbox(self) -> None:
        """Warm Pyodide up front so the first strategy is not the one that waits.

        A missing sandbox must not stop the rest of the app; the scratchpad
        route reports it and every other panel keeps working.
        """
        if not self.sandbox.is_available():
            logger.warning("strategy sandbox unavailable: %s", self.sandbox.unavailable_reason())
            return
        try:
            self.sandbox.start()
        except Exception as exc:  # noqa: BLE001 - never fail startup over the sandbox
            logger.error("strategy sandbox failed to start: %s", exc)

    def stop(self) -> None:
        self.feed.stop()
        self.sandbox.stop()

    # ---- tick handling -----------------------------------------------

    def _on_tick(self, tick: Tick) -> None:
        self._record_history(tick)
        with self._lock:
            subscribers = list(self._subscribers)
        for handler in subscribers:
            #: A failing subscriber must not stop the others or the feed thread.
            try:
                handler(tick)
            except Exception as exc:  # noqa: BLE001
                logger.warning("tick subscriber failed: %s", exc)

    def _record_history(self, tick: Tick) -> None:
        """Sample into history on an interval, not on every tick.

        At full tick rate a 200-symbol universe would fill the correlation
        window in seconds and measure microstructure noise rather than the
        day's co-movement.
        """
        now = time.monotonic()
        if now - self._last_history_write < HISTORY_INTERVAL_SECONDS:
            return
        self._last_history_write = now
        for symbol, value in self.moves().items():
            self.history.record(symbol, value)

    def subscribe_async(self, handler) -> None:
        with self._lock:
            self._subscribers.append(handler)

    def unsubscribe_async(self, handler) -> None:
        with self._lock:
            if handler in self._subscribers:
                self._subscribers.remove(handler)

    # ---- reads -------------------------------------------------------

    def ticks(self) -> dict[str, Tick]:
        return self.feed.snapshot()

    def moves(self) -> dict[str, float]:
        return {
            symbol: tick.change_pct
            for symbol, tick in self.ticks().items()
            if tick.change_pct is not None
        }

    def prices(self) -> dict[str, float]:
        return {symbol: tick.ltp for symbol, tick in self.ticks().items()}

    def status(self) -> FeedStatus:
        return FeedStatus(
            mode=self.feed_mode,
            connected=self.feed.is_connected,
            instruments=self.feed.instrument_count,
            symbols_priced=len(self.ticks()),
            detail=self.feed_detail,
        )

    def login_kotak(self) -> tuple[bool, str]:
        """Establish a Kotak session on demand. Sessions expire daily.

        The feed is not swapped underneath a running app: switching a live
        socket in place mid-session is a separate concern, and a restart picks
        up the working credentials cleanly.
        """
        from ..feed import KotakAuthError, KotakSession

        settings = KotakSettings()
        session = self.kotak_session or KotakSession(settings)
        self.kotak_session = session
        try:
            session.login()
        except KotakAuthError as exc:
            session.record_failure(str(exc))
            logger.warning("Kotak login failed: %s", exc)
            return False, str(exc)
        except Exception as exc:  # noqa: BLE001 - SDK raises bare exceptions
            session.record_failure(str(exc))
            logger.exception("Kotak login failed")
            return False, f"Login failed: {exc}"

        if self.feed_mode == "simulated":
            return True, (
                "Session established. The feed is still simulated for this process; "
                "restart the app to stream live prices."
            )
        return True, "Session established."

    def news_for(self, symbol: str, limit: int = 20) -> list[NewsItem]:
        return self.news.for_node(symbol, limit=limit)

    def build_snapshot(self) -> MarketSnapshot:
        """Freeze the current market into the shape a strategy receives."""
        ticks = self.ticks()
        symbols = list(ticks)
        return MarketSnapshot(
            taken_at=time.time(),
            prices={
                symbol: {
                    "ltp": tick.ltp,
                    "change_pct": tick.change_pct,
                    "open_interest": tick.open_interest,
                    "volume": tick.volume,
                    "segment": str(tick.segment),
                }
                for symbol, tick in ticks.items()
            },
            peers={s: self.repo.peers_of(s) for s in symbols},
            sectors={
                s: node.sector for s in symbols if (node := self.repo.get(s)) and node.sector
            },
            sector_members=self._sector_members(symbols),
            news={
                s: [
                    {"title": i.title, "ts": i.ts, "source": i.source}
                    for i in self.news.for_node(s, limit=5)
                ]
                for s in symbols
            },
            fo_symbols=[s for s in symbols if (node := self.repo.get(s)) and node.fo],
        )

    def _sector_members(self, symbols: list[str]) -> dict[str, list[str]]:
        sectors = {
            node.sector for s in symbols if (node := self.repo.get(s)) and node.sector
        }
        return {sector: self.repo.sector_members(sector) for sector in sectors}
