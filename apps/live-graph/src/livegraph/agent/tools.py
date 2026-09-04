"""Tools the analyst agent calls.

Each returns plain JSON-friendly data and does its own arithmetic, so the model
never has to compute a number it might get wrong. Flat argument lists and small
return payloads, because tool-calling fidelity through the proxy varies by
backend.
"""

from __future__ import annotations

from ..graph import EdgeType, ImpactPropagator
from .deps import AnalystDeps

#: Cap list-returning tools so a reply cannot be swamped by 500 rows.
_MAX_ROWS = 25


def quote(deps: AnalystDeps, symbol: str) -> dict:
    """Last price and percentage move for one symbol."""
    key = symbol.strip().upper()
    prices, moves = deps.prices(), deps.moves()
    if key not in prices and key not in moves:
        return {"symbol": key, "error": "no live price for this symbol"}
    node = deps.repo.get(key)
    return {
        "symbol": key,
        "ltp": prices.get(key),
        "change_pct": moves.get(key),
        "sector": node.sector if node else None,
        "fo": node.fo if node else None,
    }


def top_movers(deps: AnalystDeps, direction: str = "both", limit: int = 10) -> dict:
    """Largest movers right now. `direction` is up, down or both."""
    moves = deps.moves()
    if not moves:
        return {"rows": [], "note": "no live prices yet"}
    ordered = sorted(moves.items(), key=lambda kv: kv[1], reverse=True)
    if direction == "up":
        rows = ordered[:limit]
    elif direction == "down":
        rows = list(reversed(ordered))[:limit]
    else:
        rows = sorted(moves.items(), key=lambda kv: -abs(kv[1]))[:limit]
    return {"rows": [{"symbol": s, "change_pct": round(m, 2)} for s, m in rows[:_MAX_ROWS]]}


def neighbours(deps: AnalystDeps, symbol: str) -> dict:
    """Every node directly connected to `symbol`, with edge type, sign and live move."""
    key = symbol.strip().upper()
    if deps.repo.get(key) is None:
        return {"symbol": key, "error": "not in the graph"}
    moves = deps.moves()
    rows = [
        {
            "node": n.node.id,
            "type": str(n.edge.type),
            "sign": n.edge.sign,
            "strength": n.edge.strength,
            "direction": "outbound" if n.outbound else "inbound",
            "change_pct": moves.get(n.node.id),
            "note": n.edge.note,
        }
        for n in deps.repo.neighbours(key)
        if n.edge.type is not EdgeType.IN_SECTOR
    ]
    rows.sort(key=lambda r: -r["strength"])
    return {"symbol": key, "rows": rows[:_MAX_ROWS]}


def peer_comparison(deps: AnalystDeps, symbol: str) -> dict:
    """How `symbol` is moving against its peer group and its sector."""
    key = symbol.strip().upper()
    node = deps.repo.get(key)
    if node is None:
        return {"symbol": key, "error": "not in the graph"}
    moves = deps.moves()
    if key not in moves:
        return {"symbol": key, "error": "no live price for this symbol"}

    peers = [{"symbol": p, "change_pct": moves[p]} for p in deps.repo.peers_of(key) if p in moves]
    members = [
        {"symbol": m, "change_pct": moves[m]}
        for m in deps.repo.sector_members(node.sector or "")
        if m in moves and m != key
    ]
    return {
        "symbol": key,
        "change_pct": moves[key],
        "sector": node.sector,
        "peer_groups": list(node.peer_groups),
        "peers": peers[:_MAX_ROWS],
        "peer_avg": _mean(peers),
        "sector_members": members[:_MAX_ROWS],
        "sector_avg": _mean(members),
    }


def propagate_impact(deps: AnalystDeps, origin: str, direction: str = "up") -> dict:
    """Rank what the graph says is affected when `origin` moves.

    `origin` may be a stock or a macro node such as CRUDE or USDINR.
    """
    key = origin.strip().upper()
    if deps.repo.get(key) is None:
        return {"origin": key, "error": "not in the graph"}
    sign = 1 if direction.strip().lower() in {"up", "+", "positive", "rise"} else -1
    moves = deps.moves()
    impacts = ImpactPropagator(deps.repo).propagate(key, sign)
    return {
        "origin": key,
        "direction": direction,
        "rows": [
            {
                "symbol": impact.node_id,
                "expected": impact.direction,
                "relative_magnitude": round(impact.score, 3),
                "hops": impact.hops,
                "path": " -> ".join(impact.path),
                "actual_change_pct": moves.get(impact.node_id),
            }
            for impact in impacts[:_MAX_ROWS]
        ],
    }


def recent_news(deps: AnalystDeps, symbol: str, limit: int = 5) -> dict:
    """Headlines already tagged to `symbol` by the news resolver."""
    key = symbol.strip().upper()
    items = deps.news_for(key)[:limit]
    return {
        "symbol": key,
        "rows": [{"title": i.title, "source": i.source, "ts": i.ts, "link": i.link} for i in items],
    }


def proposed_edges(deps: AnalystDeps, limit: int = 10) -> dict:
    """Correlated pairs the graph does not connect. Candidates, not conclusions."""
    proposals = deps.comovement.propose(
        has_edge=lambda a, b: _has_edge(deps, a, b),
        same_sector=lambda a, b: _same_sector(deps, a, b),
        limit=limit,
    )
    return {
        "rows": [
            {
                "source": p.source,
                "target": p.target,
                "correlation": p.correlation,
                "samples": p.samples,
                "same_sector": p.same_sector,
                "confidence": p.confidence,
            }
            for p in proposals
        ],
        "caveat": "Correlation is not a relationship. These need human review before being added.",
    }


# ---- helpers ---------------------------------------------------------


def _mean(rows: list[dict]) -> float | None:
    if not rows:
        return None
    return round(sum(r["change_pct"] for r in rows) / len(rows), 2)


def _has_edge(deps: AnalystDeps, left: str, right: str) -> bool:
    return any(
        n.node.id == right and n.edge.type is not EdgeType.IN_SECTOR
        for n in deps.repo.neighbours(left)
    )


def _same_sector(deps: AnalystDeps, left: str, right: str) -> bool:
    a, b = deps.repo.get(left), deps.repo.get(right)
    return bool(a and b and a.sector and a.sector == b.sector)
