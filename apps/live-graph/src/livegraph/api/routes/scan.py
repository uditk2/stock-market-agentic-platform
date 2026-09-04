"""The movers scan and the per-stock drill-down."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from ...scan import VERDICT_LABEL, MoverRow, SectorContext, StockScan, Verdict
from ..deps import get_state
from ..schemas_scan import (
    DriverOut,
    NarrationOut,
    EvidenceOut,
    MoverOut,
    MoversOut,
    NewsOut,
    PeerOut,
    SectorDetailOut,
    SectorOut,
    StockScanOut,
)
from ..state import AppState
from .graph import sectors as sector_rollup

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scan", tags=["scan"])


@router.get("/movers", response_model=MoversOut)
def movers(
    per_side: int = Query(default=10, ge=1, le=100),
    state: AppState = Depends(get_state),
) -> MoversOut:
    gainers, losers = state.scan.movers(per_side=per_side)
    return MoversOut(
        gainers=[_mover(r) for r in gainers],
        losers=[_mover(r) for r in losers],
        sectors=sector_rollup(state),
    )


@router.get("/stock/{symbol}", response_model=StockScanOut)
async def stock(
    symbol: str,
    search_web: bool = Query(
        default=False,
        description="Search the web when no headline is tagged to this stock. Slow.",
    ),
    narrate: bool = Query(
        default=True,
        description=(
            "Have the agent explain the verdict. Reused for the rest of the day "
            "unless the news, the move, or the verdict changes."
        ),
    ),
    state: AppState = Depends(get_state),
) -> StockScanOut:
    key = symbol.strip().upper()
    if state.repo.get(key) is None:
        raise HTTPException(status_code=404, detail=f"{key} is not in the graph")

    scan = state.scan.stock(key, search_web=search_web)
    out = _stock_out(scan, state.scan.explain(scan), state.scan.sector_context(key))
    out.narration = await _narrate(state, scan) if narrate else None
    return out


async def _narrate(state: AppState, scan) -> NarrationOut | None:
    """A model that is unreachable must not take the whole page down with it."""
    try:
        result = await state.narrator.narrate(scan)
    except Exception as exc:  # noqa: BLE001 - the deterministic verdict still stands
        logger.warning("narration failed for %s: %s", scan.symbol, exc)
        return None
    return NarrationOut(
        text=result.text, written_at=result.written_at,
        from_cache=result.from_cache, refreshed_because=result.refreshed_because,
    )


@router.get("/sector/{name}", response_model=SectorDetailOut)
def sector(name: str, state: AppState = Depends(get_state)) -> SectorDetailOut:
    members = state.scan.sector_rows(name)
    if not members:
        raise HTTPException(status_code=404, detail=f"no priced members in {name}")
    context = state.scan.sector_context(members[0].symbol)
    if context is None:
        raise HTTPException(status_code=404, detail=f"no sector context for {name}")
    return SectorDetailOut(sector=_sector(context), members=[_mover(m) for m in members])


# ---- mapping ---------------------------------------------------------


def _mover(row: MoverRow) -> MoverOut:
    return MoverOut(
        symbol=row.symbol, name=row.name, sector=row.sector,
        ltp=round(row.ltp, 2), change_pct=round(row.change_pct, 2),
        verdict=str(row.verdict), verdict_label=VERDICT_LABEL[row.verdict],
    )


def _sector(context: SectorContext) -> SectorOut:
    return SectorOut(
        name=context.name, avg_change_pct=round(context.avg_change_pct, 2),
        advancing=context.advancing, declining=context.declining,
        breadth=context.breadth, one_sided=context.is_one_sided,
    )


def _stock_out(scan: StockScan, why: str, context: SectorContext | None) -> StockScanOut:
    evidence = scan.evidence
    peer_avg = evidence.peer_avg
    conflicting = {d.node for d in evidence.conflicting_drivers}
    return StockScanOut(
        symbol=scan.symbol, name=scan.name, sector=scan.sector,
        peer_groups=list(scan.peer_groups),
        ltp=round(scan.ltp, 2), change_pct=round(scan.change_pct, 2),
        verdict=str(scan.verdict), verdict_label=VERDICT_LABEL[scan.verdict], why=why,
        evidence=EvidenceOut(
            change_pct=round(evidence.change_pct, 2),
            peer_avg=None if peer_avg is None else round(peer_avg, 2),
            peer_count=evidence.peer_count,
            gap=None if evidence.gap is None else round(evidence.gap, 2),
            news_counts=evidence.news_counts,
        ),
        sector_context=None if context is None else _sector(context),
        peers=[
            PeerOut(
                symbol=p.symbol, change_pct=round(p.change_pct, 2),
                vs_peer_avg=round(p.change_pct - (peer_avg or 0.0), 2),
            )
            for p in sorted(scan.peers, key=lambda p: -p.change_pct)
        ],
        drivers=[
            DriverOut(
                edge_type=d.edge_type, node=d.node, sign=d.sign, strength=d.strength,
                note=d.note,
                driver_change_pct=None if d.driver_change_pct is None else round(d.driver_change_pct, 2),
                expected_direction=d.expected_direction,
                conflicting=d.node in conflicting,
            )
            for d in scan.drivers
        ],
        news=[
            NewsOut(
                scope=str(n.scope), title=n.title, source=n.source,
                ts=n.ts, link=n.link, matched_node=n.matched_node,
            )
            for n in scan.news
        ],
    )
