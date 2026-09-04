"""Parse stock_graph.json into typed GraphData."""

from __future__ import annotations

import json
from pathlib import Path

from .models import Edge, EdgeType, GraphData, Node, NodeType


def load_graph(path: Path) -> GraphData:
    raw = json.loads(path.read_text(encoding="utf-8"))
    nodes = {n.id: n for n in (_parse_node(item) for item in raw.get("nodes", []))}
    edges = [edge for item in raw.get("edges", []) if (edge := _parse_edge(item, nodes))]
    return GraphData(nodes=nodes, edges=edges)


def _parse_node(item: dict) -> Node:
    peer_groups = item.get("peer_groups") or ()
    return Node(
        id=str(item["id"]),
        type=NodeType(item["type"]),
        label=str(item.get("label") or item["id"]),
        name=str(item.get("name") or item.get("label") or item["id"]),
        sector=item.get("sector"),
        isin=item.get("isin"),
        fo=bool(item.get("fo", False)),
        tier=item.get("tier"),
        peer_groups=tuple(str(g) for g in peer_groups),
    )


def _parse_edge(item: dict, nodes: dict[str, Node]) -> Edge | None:
    """Drop edges pointing at unknown nodes rather than failing the whole load."""
    source, target = str(item["source"]), str(item["target"])
    if source not in nodes or target not in nodes:
        return None
    return Edge(
        source=source,
        target=target,
        type=EdgeType(item["type"]),
        strength=float(item.get("strength", 0.0)),
        sign=int(item.get("sign", 0)),
        note=item.get("note"),
    )
