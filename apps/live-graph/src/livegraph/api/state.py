"""The single place feed, graph and news are joined.

Those three modules never import one another; everything that needs more than
one of them goes through AppState.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from ..agent import AnalystDeps, AnalystService, CoMovementAnalyzer, PriceHistory
from ..feed import KotakSession, KotakSettings, NoFeed, Segment, Tick
from ..feed.config import load_kotak_settings
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
    #: Tells "the socket is silent" apart from "frames arrive and match
    #: nothing". Both look like an empty screen and have different fixes.
    frames_received: int = 0
    frames_unmatched: int = 0
    #: Kotak ended the session. The feed cannot recover on its own; the tab
    #: should ask for a login rather than showing a live mode with no prices.
    session_ended: bool = False


class AppState:
    def __init__(self, data_dir: Path | None = None, feed=None):
        resolved = data_dir or resolve_data_dir()
        self.repo = GraphRepository.from_file(resolved / "stock_graph.json")
        self.history = PriceHistory()
        self.comovement = CoMovementAnalyzer(self.history)
        self.sandbox = PyodideSandbox()
        self.news = self._build_news(resolved)
        self.feed, self.feed_mode, self.feed_detail = self._resolve_feed(feed)
        self.kotak_session: "KotakSession | None" = None
        self._last_history_write = 0.0
        self._loop = None
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

    def _resolve_feed(self, injected):
        """Live Kotak, or nothing at all.

        There is deliberately no synthetic fallback. A feed that invents prices
        can be mistaken for the market, and every screen here is built to be
        acted on. When credentials are absent or a login fails the app runs with
        no prices and says why, rather than showing numbers that are not real.
        """
        if injected is not None:
            return injected, "injected", "feed supplied by the caller"

        settings = load_kotak_settings()
        missing = settings.missing_fields()
        if missing:
            detail = f"Kotak credentials incomplete: {', '.join(missing)}"
            logger.warning("%s; running without prices", detail)
            return NoFeed(detail), "unconfigured", detail

        try:
            return self._live_feed(settings)
        except Exception as exc:  # noqa: BLE001 - startup must survive a bad login
            detail = f"Kotak login failed: {exc}"
            logger.error(detail)
            return NoFeed(detail), "error", detail

    def _live_feed(self, settings: KotakSettings):
        from ..feed import KotakSession

        session = KotakSession(settings)
        self.kotak_session = session
        return self._live_feed_from(session.login())

    def _live_feed_from(self, client):
        """Everything after the login: resolve contracts and build the stream."""
        from ..feed import (
            TickStream,
            load_scrip_master,
            nearest_expiry_per_underlying,
            parse_instruments,
        )

        #: `scrip_master` answers with a URL to a CSV, not with rows.
        rows = load_scrip_master(client.scrip_master(exchange_segment=str(Segment.FNO)))
        instruments = nearest_expiry_per_underlying(parse_instruments(rows, Segment.FNO))
        tradable = {n.id for n in self.repo.nodes_of_type(NodeType.STOCK)}
        selected = [i for i in instruments if i.underlying in tradable]
        if not selected:
            raise RuntimeError("no F&O contract matched a graph symbol")
        stream = TickStream(client, selected, loop=self._loop)
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
        #: Captured here because this runs on the event loop, and a feed built
        #: later from an admin request will not be: that thread has no loop to
        #: find, and the stream needs one to hand ticks back to the app.
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None
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
            frames_received=getattr(self.feed, "frames_received", 0),
            frames_unmatched=getattr(self.feed, "frames_unmatched", 0),
            session_ended=getattr(self.feed, "session_ended", False),
        )

    def login_kotak(self, totp: str | None = None, mpin: str | None = None) -> tuple[bool, str]:
        """Establish a Kotak session on demand. Sessions expire daily.

        `totp` and `mpin` are the two per-login values. Passing either removes
        the need for it to be stored, which is what lets somebody log in from
        the Admin tab with the code read off their authenticator and the MPIN
        typed rather than written to disk.
        """
        from ..feed import KotakAuthError, KotakSession

        settings = load_kotak_settings()
        session = self.kotak_session or KotakSession(settings)
        self.kotak_session = session
        try:
            session.login(totp=totp, mpin=mpin)
        except KotakAuthError as exc:
            session.record_failure(str(exc))
            logger.warning("Kotak login failed: %s", exc)
            return False, str(exc)
        except Exception as exc:  # noqa: BLE001 - SDK raises bare exceptions
            session.record_failure(str(exc))
            logger.exception("Kotak login failed")
            return False, f"Login failed: {exc}"

        if self.feed_mode == "live":
            #: Already streaming. Replacing a live socket in place is a separate
            #: concern from starting one, and the session just refreshed is the
            #: thing that keeps the existing stream working.
            return True, "Session established."

        return self._start_live_feed(session.client)

    def _start_live_feed(self, client) -> tuple[bool, str]:
        """Swap a NoFeed for a real stream after a successful manual login.

        Safe precisely because there is nothing live to tear down: the app
        started unconfigured, so no socket, no handlers and no prices exist yet.
        A restart would also work and is what this used to require, which made
        the Admin tab able to log in and unable to show a price.
        """
        from ..feed import NoFeed

        if not isinstance(self.feed, NoFeed):
            #: An injected test feed, or something else deliberate. Not ours to
            #: replace on the strength of a login.
            return True, "Session established. The existing feed was left alone."

        previous = self.feed
        try:
            stream, mode, detail = self._live_feed_from(client)
            self.feed = stream
            self.feed_mode, self.feed_detail = mode, detail
            self.feed.add_handler(self._on_tick)
            #: Inside the try. `start()` is where the subscribe happens, so a
            #: failure here leaves a feed that is registered and not listening —
            #: the app claiming to be live while no tick can arrive.
            self.feed.start()
        except Exception as exc:  # noqa: BLE001 - the login worked; this is separate
            logger.exception("could not start the feed after login")
            self.feed = previous
            self.feed_mode, self.feed_detail = "error", f"feed did not start: {exc}"
            return True, (
                f"Session established, but the feed did not start: {exc}. "
                "Restarting the app will retry it."
            )

        logger.info("feed started after manual login: %s", detail)
        return True, f"Session established and the feed is live: {detail}."

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
                    {"title": i.title, "ts": i.ts, "source": i.source, "kind": str(i.kind)}
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
