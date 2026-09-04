"""Tagged news headlines."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from ..deps import get_state
from ..schemas import NewsItemOut
from ..state import AppState

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("", response_model=list[NewsItemOut])
def recent(
    limit: int = Query(default=50, ge=1, le=200),
    fo_only: bool = Query(default=False),
    state: AppState = Depends(get_state),
) -> list[NewsItemOut]:
    return [_to_out(item) for item in state.news.recent(limit=limit, fo_only=fo_only)]


@router.get("/symbol/{symbol}", response_model=list[NewsItemOut])
def for_symbol(
    symbol: str,
    limit: int = Query(default=20, ge=1, le=100),
    state: AppState = Depends(get_state),
) -> list[NewsItemOut]:
    return [_to_out(item) for item in state.news_for(symbol.strip().upper(), limit=limit)]


@router.post("/refresh")
def refresh(background: BackgroundTasks, state: AppState = Depends(get_state)) -> dict:
    """Poll every feed now. Runs in the background so the request returns at once."""
    background.add_task(state.news.poll_once)
    return {"started": True}


@router.get("/health", response_model=list[dict])
def health(state: AppState = Depends(get_state)) -> list[dict]:
    return [asdict(h) for h in state.news.health.values()]


def _to_out(item) -> NewsItemOut:
    return NewsItemOut(
        title=item.title, link=item.link, summary=item.summary, ts=item.ts,
        source=item.source, entities=item.entities, fo=item.fo,
    )
