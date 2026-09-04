"""Strategy scratchpad: write a strategy in English, run it on a live snapshot."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...scratchpad.thread import ScratchpadService, ScratchpadThread
from ..deps import get_state
from ..schemas import ScratchpadSendIn, ScratchpadTurnOut
from ..state import AppState

router = APIRouter(prefix="/api/scratchpad", tags=["scratchpad"])

_THREADS: dict[str, ScratchpadThread] = {}
_SERVICE: ScratchpadService | None = None


def _service(state: AppState) -> ScratchpadService:
    """Built lazily: constructing it opens a model client we do not want at import."""
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = ScratchpadService(sandbox=state.sandbox)
    return _SERVICE


@router.get("/health")
def health(state: AppState = Depends(get_state)) -> dict:
    available = state.sandbox.is_available()
    return {
        "sandbox_available": available,
        "runtime": state.sandbox.name,
        "detail": "" if available else state.sandbox.unavailable_reason(),
    }


@router.get("/threads")
def threads() -> list[dict]:
    return [
        {"id": t.id, "title": t.title, "turns": t.turn_count, "has_strategy": bool(t.latest_code)}
        for t in _THREADS.values()
    ]


@router.post("/send", response_model=ScratchpadTurnOut)
async def send(body: ScratchpadSendIn, state: AppState = Depends(get_state)) -> ScratchpadTurnOut:
    if not state.sandbox.is_available():
        raise HTTPException(status_code=503, detail=health(state)["detail"])

    thread = _get_or_create(body.thread_id)
    if thread.turn_count == 0:
        thread.title = body.prompt[:60]

    turn = await _service(state).send(thread, body.prompt, state.build_snapshot())
    return _to_out(thread, turn)


@router.post("/rerun/{thread_id}", response_model=ScratchpadTurnOut)
async def rerun(thread_id: str, state: AppState = Depends(get_state)) -> ScratchpadTurnOut:
    """Re-execute the stored strategy on a fresh snapshot. No model call."""
    thread = _THREADS.get(thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="unknown thread")

    run = await _service(state).rerun(thread, state.build_snapshot())
    return ScratchpadTurnOut(
        thread_id=thread.id, status=str(run.status), code=thread.latest_code,
        explanation="", output=run.output, figures=list(run.figures),
        stdout=run.stdout, error=run.error, duration_ms=run.duration_ms,
    )


def _get_or_create(thread_id: str | None) -> ScratchpadThread:
    if thread_id:
        if thread_id not in _THREADS:
            raise HTTPException(status_code=404, detail="unknown thread")
        return _THREADS[thread_id]
    thread = ScratchpadThread()
    _THREADS[thread.id] = thread
    return thread


def _to_out(thread: ScratchpadThread, turn) -> ScratchpadTurnOut:
    run, draft = turn.run, turn.draft
    return ScratchpadTurnOut(
        thread_id=thread.id,
        status=str(run.status),
        code=draft.code if draft else "",
        explanation=draft.explanation if draft else "",
        output=run.output,
        figures=list(run.figures),
        stdout=run.stdout,
        error=run.error,
        repairs=turn.repairs,
        duration_ms=run.duration_ms,
    )
