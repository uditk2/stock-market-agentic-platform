"""Live prices and the deterministic detectors over them."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query

from ..deps import get_state
from ..schemas import EdgeProposalOut, FeedStatusOut, QuoteOut
from ..state import AppState

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/status", response_model=FeedStatusOut)
def feed_status(state: AppState = Depends(get_state)) -> FeedStatusOut:
    return FeedStatusOut(**asdict(state.status()))


@router.get("/quotes", response_model=list[QuoteOut])
def quotes(state: AppState = Depends(get_state)) -> list[QuoteOut]:
    return [
        QuoteOut(
            symbol=symbol,
            ltp=tick.ltp,
            change_pct=tick.change_pct,
            open_interest=tick.open_interest,
            volume=tick.volume,
            segment=str(tick.segment),
            ts=tick.ts,
        )
        for symbol, tick in sorted(state.ticks().items())
    ]


@router.get("/movers", response_model=list[QuoteOut])
def movers(
    limit: int = Query(default=20, ge=1, le=100),
    direction: str = Query(default="both", pattern="^(up|down|both)$"),
    state: AppState = Depends(get_state),
) -> list[QuoteOut]:
    rows = quotes(state)
    priced = [row for row in rows if row.change_pct is not None]
    if direction == "up":
        priced.sort(key=lambda r: -r.change_pct)
    elif direction == "down":
        priced.sort(key=lambda r: r.change_pct)
    else:
        priced.sort(key=lambda r: -abs(r.change_pct))
    return priced[:limit]


@router.get("/edge-proposals", response_model=list[EdgeProposalOut])
def edge_proposals(
    limit: int = Query(default=20, ge=1, le=100),
    state: AppState = Depends(get_state),
) -> list[EdgeProposalOut]:
    from ...graph import EdgeType

    def has_edge(left: str, right: str) -> bool:
        return any(
            n.node.id == right and n.edge.type is not EdgeType.IN_SECTOR
            for n in state.repo.neighbours(left)
        )

    def same_sector(left: str, right: str) -> bool:
        a, b = state.repo.get(left), state.repo.get(right)
        return bool(a and b and a.sector and a.sector == b.sector)

    return [
        EdgeProposalOut(**asdict(p))
        for p in state.comovement.propose(has_edge, same_sector, limit=limit)
    ]
