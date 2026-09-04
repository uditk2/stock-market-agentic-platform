"""Graph structure, overlaid with whatever prices are live."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ...graph import EdgeType, ImpactPropagator, NodeType
from ..deps import get_state
from ..schemas import GraphEdgeOut, GraphNodeOut, GraphOut, ImpactRowOut
from ..state import AppState

router = APIRouter(prefix="/api/graph", tags=["graph"])

#: Rendering 3003 edges at once is unreadable and slow in the browser, so the
#: default view is the F&O tier with membership edges dropped.
_MEMBERSHIP = EdgeType.IN_SECTOR


@router.get("", response_model=GraphOut)
def full_graph(
    fo_only: bool = Query(default=True),
    include_sectors: bool = Query(default=True),
    state: AppState = Depends(get_state),
) -> GraphOut:
    moves, prices = state.moves(), state.prices()
    keep = _visible_node_ids(state, fo_only, include_sectors)

    nodes = [
        _to_node(state.repo.require(node_id), moves, prices)
        for node_id in sorted(keep)
    ]
    edges = [
        GraphEdgeOut(
            source=edge.source, target=edge.target, type=str(edge.type),
            sign=edge.sign, strength=edge.strength, note=edge.note,
        )
        for node_id in keep
        for edge in state.repo.outgoing(node_id)
        if edge.target in keep and (include_sectors or edge.type is not _MEMBERSHIP)
    ]
    return GraphOut(nodes=nodes, edges=edges)


@router.get("/node/{symbol}", response_model=GraphOut)
def neighbourhood(
    symbol: str,
    depth: int = Query(default=1, ge=1, le=2),
    state: AppState = Depends(get_state),
) -> GraphOut:
    """One node and everything within `depth` hops, membership edges excluded."""
    key = symbol.strip().upper()
    if state.repo.get(key) is None:
        raise HTTPException(status_code=404, detail=f"{key} is not in the graph")

    keep = {key}
    frontier = {key}
    for _ in range(depth):
        discovered = {
            n.node.id
            for node_id in frontier
            for n in state.repo.neighbours(node_id)
            if n.edge.type is not _MEMBERSHIP
        }
        frontier = discovered - keep
        keep |= discovered

    moves, prices = state.moves(), state.prices()
    return GraphOut(
        nodes=[_to_node(state.repo.require(n), moves, prices) for n in sorted(keep)],
        edges=[
            GraphEdgeOut(
                source=edge.source, target=edge.target, type=str(edge.type),
                sign=edge.sign, strength=edge.strength, note=edge.note,
            )
            for node_id in keep
            for edge in state.repo.outgoing(node_id)
            if edge.target in keep and edge.type is not _MEMBERSHIP
        ],
    )


@router.get("/impact/{origin}", response_model=list[ImpactRowOut])
def impact(
    origin: str,
    direction: str = Query(default="up", pattern="^(up|down)$"),
    limit: int = Query(default=30, ge=1, le=100),
    state: AppState = Depends(get_state),
) -> list[ImpactRowOut]:
    key = origin.strip().upper()
    if state.repo.get(key) is None:
        raise HTTPException(status_code=404, detail=f"{key} is not in the graph")

    moves = state.moves()
    impacts = ImpactPropagator(state.repo).propagate(key, 1 if direction == "up" else -1)
    return [
        ImpactRowOut(
            symbol=i.node_id,
            expected=i.direction,
            relative_magnitude=round(i.score, 3),
            hops=i.hops,
            path=" -> ".join(i.path),
            actual_change_pct=moves.get(i.node_id),
        )
        for i in impacts[:limit]
    ]


@router.get("/sectors", response_model=list[dict])
def sectors(state: AppState = Depends(get_state)) -> list[dict]:
    """Sector roll-up: average move and breadth across priced members."""
    moves = state.moves()
    rows = []
    for hub in state.repo.nodes_of_type(NodeType.SECTOR):
        name = hub.id.removeprefix("SEC::")
        members = state.repo.sector_members(name)
        priced = [moves[m] for m in members if m in moves]
        if not priced:
            continue
        rows.append({
            "sector": name,
            "members": len(members),
            "priced": len(priced),
            "avg_change_pct": round(sum(priced) / len(priced), 2),
            "advancing": sum(1 for v in priced if v > 0),
            "declining": sum(1 for v in priced if v < 0),
        })
    rows.sort(key=lambda r: -r["avg_change_pct"])
    return rows


def _visible_node_ids(state: AppState, fo_only: bool, include_sectors: bool) -> set[str]:
    stocks = state.repo.nodes_of_type(NodeType.STOCK)
    keep = {n.id for n in stocks if n.fo or not fo_only}
    keep |= {n.id for n in state.repo.nodes_of_type(NodeType.MACRO)}
    if include_sectors:
        keep |= {n.id for n in state.repo.nodes_of_type(NodeType.SECTOR)}
    return keep


def _to_node(node, moves: dict[str, float], prices: dict[str, float]) -> GraphNodeOut:
    return GraphNodeOut(
        id=node.id, label=node.label, name=node.name, type=str(node.type),
        sector=node.sector, fo=node.fo, peer_groups=list(node.peer_groups),
        change_pct=moves.get(node.id), ltp=prices.get(node.id),
    )
