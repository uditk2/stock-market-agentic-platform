"""Live tick stream over the Neo WebSocket.

The SDK invokes callbacks on its own socket thread, so every handoff into the
asyncio world goes through `call_soon_threadsafe`. Nothing here knows about the
graph; it emits Ticks and holds the latest value per underlying.
"""

from __future__ import annotations

import asyncio
import logging
import re
import threading
from collections.abc import Callable, Iterable

from .models import Instrument, Segment, Tick
from .normalizer import TickNormalizer

logger = logging.getLogger(__name__)

#: Kotak rejects oversized subscribe frames, so batch the token list.
SUBSCRIBE_BATCH_SIZE = 100

#: Rising, and finite. A blip clears in seconds; anything still failing after
#: this is an expired session, which no amount of retrying will fix.
RECONNECT_BACKOFF_SECONDS = (2, 5, 15, 30, 60)

#: Kotak's own words when the session, not merely the socket, has ended.
_SESSION_ENDED = re.compile(r"session\s+has\s+been\s+closed", re.I)

TickHandler = Callable[[Tick], None]


class TickStream:
    def __init__(self, client, instruments: Iterable[Instrument], loop=None):
        self._client = client
        self._instruments = list(instruments)
        self._by_token = {i.instrument_token: i for i in self._instruments}
        self._normalizer = TickNormalizer(self._by_token)
        self._loop = loop
        self._lock = threading.Lock()
        self._latest: dict[str, Tick] = {}
        self._handlers: list[TickHandler] = []
        self._connected = threading.Event()
        #: "No prices" has three causes that look identical from outside: no
        #: frame arrived, frames arrived carrying no price, or they carried a
        #: token this stream never subscribed to. Counting them apart is the
        #: difference between a diagnosis and a guess.
        self._frames = 0
        self._unmatched = 0
        self._logged_sample = False
        #: Kotak drops the socket — idle timeouts, network blips, a session
        #: ending. Nothing here reconnected, so the first drop was permanent
        #: and the app went on reporting a live feed with no prices behind it.
        self._stopping = threading.Event()
        self._reconnects = 0
        #: One reconnect at a time. Kotak emits a close per subscribed batch,
        #: so a single drop arrives as many closes; spawning a thread for each
        #: turned one dropped socket into a storm that resubscribed, closed,
        #: and spawned again until the log was the only thing still working.
        self._reconnecting = threading.Event()
        #: Set when Kotak says the session itself has ended. No amount of
        #: resubscribing fixes that: it needs a fresh TOTP, which only a person
        #: has. Retrying against it is the loop described above.
        self._session_ended = False

    # ---- lifecycle ---------------------------------------------------

    def start(self) -> None:
        self._loop = self._loop or _current_loop()
        self._client.on_message = self._on_message
        self._client.on_error = self._on_error
        self._client.on_close = self._on_close
        self._client.on_open = self._on_open
        self._subscribe_all()

    def _subscribe_all(self) -> None:
        for batch in self._batches():
            self._client.subscribe(
                instrument_tokens=[i.as_subscription() for i in batch],
                isIndex=False,
                isDepth=False,
            )
        logger.info("Subscribed to %d instruments", len(self._instruments))

    def stop(self) -> None:
        #: Set first, so the close this triggers is not mistaken for a drop.
        self._stopping.set()
        for batch in self._batches():
            try:
                self._client.un_subscribe(
                    instrument_tokens=[i.as_subscription() for i in batch],
                    isIndex=False,
                    isDepth=False,
                )
            except Exception as exc:  # noqa: BLE001 - teardown is best-effort
                logger.warning("un_subscribe failed: %s", exc)
        self._connected.clear()

    def _batches(self) -> list[list[Instrument]]:
        size = SUBSCRIBE_BATCH_SIZE
        return [
            self._instruments[i : i + size]
            for i in range(0, len(self._instruments), size)
        ]

    # ---- subscriptions -----------------------------------------------

    def add_handler(self, handler: TickHandler) -> None:
        self._handlers.append(handler)

    def remove_handler(self, handler: TickHandler) -> None:
        if handler in self._handlers:
            self._handlers.remove(handler)

    # ---- socket callbacks (run on the SDK thread) --------------------

    def _on_message(self, message) -> None:
        self._frames += 1
        try:
            ticks = self._normalizer.normalize_message(message)
        except Exception as exc:  # noqa: BLE001 - a bad frame must not kill the socket
            logger.warning("tick normalisation failed: %s", exc)
            return
        if not ticks:
            self._unmatched += 1
            self._log_unmatched_sample(message)
            return
        with self._lock:
            for tick in ticks:
                self._latest[tick.underlying] = tick
        self._dispatch(ticks)

    def _schedule_reconnect(self) -> None:
        """Re-subscribe on a background thread, backing off between tries.

        Re-subscribing is the whole of it: the SDK opens the socket as part of
        subscribing, so there is no separate connect to repeat. What this
        cannot fix is an expired Kotak session — that needs a fresh TOTP, which
        only a person has — so it gives up rather than hammering, and leaves
        `is_connected` false for the status endpoint to report.
        """
        if self._stopping.is_set() or self._session_ended:
            return
        #: The guard is the whole point: without it every close starts a thread.
        if self._reconnecting.is_set():
            return
        self._reconnecting.set()
        threading.Thread(target=self._reconnect, name="kotak-reconnect", daemon=True).start()

    def _reconnect(self) -> None:
        try:
            for attempt, delay in enumerate(RECONNECT_BACKOFF_SECONDS, start=1):
                if self._stopping.wait(delay) or self._session_ended:
                    return
                try:
                    self._subscribe_all()
                except Exception as exc:  # noqa: BLE001 - the SDK raises bare exceptions
                    logger.warning(
                        "reconnect attempt %d of %d failed: %s",
                        attempt, len(RECONNECT_BACKOFF_SECONDS), exc,
                    )
                    continue
                self._reconnects += 1
                logger.info(
                    "resubscribed after a dropped socket (%d so far)", self._reconnects
                )
                return
            logger.error(
                "could not resubscribe after %d attempts; log in again to start a "
                "new session", len(RECONNECT_BACKOFF_SECONDS),
            )
        finally:
            #: Released whatever happened, so a later, genuine drop can retry.
            self._reconnecting.clear()

    def _log_unmatched_sample(self, message) -> None:
        """Report the shape of the first frame that yielded nothing, once.

        Field names only. A frame that resolves to no instrument is either a
        token this stream did not subscribe to or a shape the normaliser does
        not know, and both are answered by seeing which keys arrived.
        """
        if self._logged_sample:
            return
        self._logged_sample = True
        first = message[0] if isinstance(message, list) and message else message
        keys = sorted(first) if isinstance(first, dict) else type(first).__name__
        logger.warning(
            "frame produced no tick; keys=%s, subscribed tokens sample=%s",
            keys, list(self._by_token)[:3],
        )

    def _dispatch(self, ticks: list[Tick]) -> None:
        if not self._handlers or self._loop is None:
            return
        for tick in ticks:
            for handler in list(self._handlers):
                self._loop.call_soon_threadsafe(_safe_call, handler, tick)

    def _on_open(self, message) -> None:
        self._connected.set()
        logger.info("Kotak socket open: %s", message)

    def _on_close(self, message) -> None:
        self._connected.clear()
        if self._stopping.is_set():
            logger.debug("Kotak socket closed during shutdown: %s", message)
            return
        if _SESSION_ENDED.search(str(message)):
            if not self._session_ended:
                self._session_ended = True
                logger.error(
                    "Kotak ended the session (%s). The socket cannot be recovered by "
                    "resubscribing; log in again to start a new one.", message,
                )
            return
        if self._reconnecting.is_set():
            #: Already handling this drop. Kotak sends one close per batch, so
            #: the rest of them are the same event arriving again.
            logger.debug("Kotak socket closed again while reconnecting: %s", message)
            return
        logger.warning("Kotak socket closed: %s", message)
        self._schedule_reconnect()

    def _on_error(self, message) -> None:
        if self._session_ended or self._reconnecting.is_set():
            #: Downstream of a close already reported. "socket is already
            #: closed" is the same fact restated, once per pending frame.
            logger.debug("Kotak socket error after close: %s", message)
            return
        if self._stopping.is_set():
            #: Teardown races: a response to our own unsubscribe arrives after
            #: the session is gone. Not a fault, and not worth a red line.
            logger.debug("Kotak socket error during shutdown: %s", message)
            return
        logger.error("Kotak socket error: %s", message)

    # ---- read access -------------------------------------------------

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    def latest(self, underlying: str) -> Tick | None:
        with self._lock:
            return self._latest.get(underlying)

    def snapshot(self, segment: Segment | None = None) -> dict[str, Tick]:
        with self._lock:
            items = self._latest.items()
            if segment is None:
                return dict(items)
            return {k: v for k, v in items if v.segment is segment}

    @property
    def instrument_count(self) -> int:
        return len(self._instruments)

    @property
    def frames_received(self) -> int:
        return self._frames

    @property
    def frames_unmatched(self) -> int:
        return self._unmatched

    @property
    def reconnects(self) -> int:
        return self._reconnects

    @property
    def session_ended(self) -> bool:
        """Kotak closed the session; only a fresh login brings prices back."""
        return self._session_ended


def _current_loop():
    """The running loop, or None when started off the loop's own thread.

    `asyncio.get_event_loop()` raises there, and this is started from two
    places: the lifespan, which runs on the loop, and an admin request, which
    runs in a worker thread. Raising in the second took down a login that had
    already succeeded and left the app claiming a feed it had not subscribed.

    None is survivable — `_dispatch` checks for it — but it means ticks reach
    no handler, so the caller is expected to pass a loop rather than rely on
    this. It exists so a missing loop degrades instead of exploding.
    """
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        logger.warning(
            "no running event loop for the tick stream; ticks will not be dispatched"
        )
        return None


def _safe_call(handler: TickHandler, tick: Tick) -> None:
    try:
        handler(tick)
    except Exception as exc:  # noqa: BLE001 - one bad handler must not stop the rest
        logger.warning("tick handler failed: %s", exc)
