"""The analyst agent, exposed as threaded chat plus three canned reviews."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from ...agent import AnalystThread
from ...llm import get_llm_settings
from ..deps import get_state
from ..schemas import AnalystReplyOut, AskIn
from ..state import AppState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analyst", tags=["analyst"])

#: Threads live for the process lifetime only; this is a local tool, not a
#: multi-user service, so there is nothing to persist yet.
_THREADS: dict[str, AnalystThread] = {}


def _thread(thread_id: str | None) -> AnalystThread:
    if thread_id and thread_id in _THREADS:
        return _THREADS[thread_id]
    if thread_id:
        raise HTTPException(status_code=404, detail="unknown thread")
    thread = AnalystThread()
    _THREADS[thread.id] = thread
    return thread


async def _reply(coro, thread: AnalystThread) -> AnalystReplyOut:
    """Turn an unreachable model into an explanation, not a bare 500.

    The commonest cause is CLIProxyAPI being unreachable from where the app is
    running, which from inside a container means "localhost" pointed at the
    container itself.
    """
    try:
        reply = await coro
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI, not swallowed
        settings = get_llm_settings()
        logger.error("analyst call failed against %s: %s", settings.cliproxy_base_url, exc)
        raise HTTPException(
            status_code=502,
            detail=(
                f"Could not reach the model at {settings.cliproxy_base_url}. "
                "Check that CLIProxyAPI is running and that the URL is reachable "
                "from this process; inside a container use host.docker.internal, "
                "not localhost."
            ),
        ) from exc
    return AnalystReplyOut(text=reply.text, thread_id=thread.id, tools_used=list(reply.tools_used))


@router.post("/ask", response_model=AnalystReplyOut)
async def ask(body: AskIn, state: AppState = Depends(get_state)) -> AnalystReplyOut:
    thread = _thread(body.thread_id)
    return await _reply(state.analyst.ask(thread, body.question), thread)


@router.post("/explain/{symbol}", response_model=AnalystReplyOut)
async def explain(symbol: str, state: AppState = Depends(get_state)) -> AnalystReplyOut:
    thread = _thread(None)
    return await _reply(state.analyst.explain(thread, symbol.strip().upper()), thread)


@router.post("/review-edge-proposals", response_model=AnalystReplyOut)
async def review_edge_proposals(state: AppState = Depends(get_state)) -> AnalystReplyOut:
    thread = _thread(None)
    return await _reply(state.analyst.review_edge_proposals(thread), thread)
