"""Live tick stream over the Neo WebSocket.

The SDK invokes callbacks on its own socket thread, so every handoff into the
asyncio world goes through `call_soon_threadsafe`. Nothing here knows about the
graph; it emits Ticks and holds the latest value per underlying.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable, Iterable

from .models import Instrument, Segment, Tick
from .normalizer import TickNormalizer

logger = logging.getLogger(__name__)

#: Kotak rejects oversized subscribe frames, so batch the token list.
SUBSCRIBE_BATCH_SIZE = 100

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

    # ---- lifecycle ---------------------------------------------------

    def start(self) -> None:
        self._loop = self._loop or asyncio.get_event_loop()
        self._client.on_message = self._on_message
        self._client.on_error = self._on_error
        self._client.on_close = self._on_close
        self._client.on_open = self._on_open
        for batch in self._batches():
            self._client.subscribe(
                instrument_tokens=[i.as_subscription() for i in batch],
                isIndex=False,
                isDepth=False,
            )
        logger.info("Subscribed to %d instruments", len(self._instruments))

    def stop(self) -> None:
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
        try:
            ticks = self._normalizer.normalize_message(message)
        except Exception as exc:  # noqa: BLE001 - a bad frame must not kill the socket
            logger.warning("tick normalisation failed: %s", exc)
            return
        if not ticks:
            return
        with self._lock:
            for tick in ticks:
                self._latest[tick.underlying] = tick
        self._dispatch(ticks)

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
        logger.warning("Kotak socket closed: %s", message)

    def _on_error(self, message) -> None:
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


def _safe_call(handler: TickHandler, tick: Tick) -> None:
    try:
        handler(tick)
    except Exception as exc:  # noqa: BLE001 - one bad handler must not stop the rest
        logger.warning("tick handler failed: %s", exc)
