"""WebSocket fan-out of live ticks.

Each client gets its own bounded queue. The feed thread never blocks on a slow
client: a full queue drops the tick, because a stale price the client will
overwrite in two seconds is not worth stalling every other client for.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .state import AppState

logger = logging.getLogger(__name__)

router = APIRouter()

QUEUE_SIZE = 500
#: Ticks are coalesced and flushed on this interval rather than sent one by one,
#: so a 200-symbol universe does not become 200 websocket frames per second.
FLUSH_INTERVAL_SECONDS = 0.5


@router.websocket("/ws/ticks")
async def ticks(websocket: WebSocket) -> None:
    await websocket.accept()
    state: AppState = websocket.app.state.livegraph
    queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
    loop = asyncio.get_running_loop()

    def on_tick(tick) -> None:
        #: Called from the feed thread, so hop back onto the loop.
        loop.call_soon_threadsafe(_offer, queue, tick)

    state.subscribe_async(on_tick)
    try:
        await websocket.send_json({"type": "snapshot", "ticks": _snapshot(state)})
        while True:
            batch = await _drain(queue)
            if batch:
                await websocket.send_json({"type": "ticks", "ticks": batch})
            await asyncio.sleep(FLUSH_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001 - one client's failure is not fatal
        logger.warning("tick websocket closed: %s", exc)
    finally:
        state.unsubscribe_async(on_tick)
        with contextlib.suppress(Exception):
            await websocket.close()


async def _drain(queue: asyncio.Queue) -> list[dict]:
    """Collapse everything queued to the latest value per symbol."""
    latest: dict[str, dict] = {}
    while not queue.empty():
        tick = queue.get_nowait()
        latest[tick.underlying] = _to_payload(tick)
    return list(latest.values())


def _offer(queue: asyncio.Queue, tick) -> None:
    try:
        queue.put_nowait(tick)
    except asyncio.QueueFull:
        pass


def _snapshot(state: AppState) -> list[dict]:
    return [_to_payload(tick) for tick in state.ticks().values()]


def _to_payload(tick) -> dict:
    return {
        "symbol": tick.underlying,
        "ltp": tick.ltp,
        "change_pct": tick.change_pct,
        "open_interest": tick.open_interest,
        "volume": tick.volume,
        "ts": tick.ts,
    }
