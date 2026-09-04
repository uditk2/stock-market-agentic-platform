"""Indexed lookups over GraphData. Read-only, no impact math."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .loader import load_graph
from .models import Edge, GraphData, Neighbour, Node, NodeType

SECTOR_PREFIX = "SEC::"


class GraphRepository:
    def __init__(self, data: GraphData):
        self._data = data
        self._outgoing: dict[str, list[Edge]] = defaultdict(list)
        self._incoming: dict[str, list[Edge]] = defaultdict(list)
        self._by_peer_group: dict[str, list[str]] = defaultdict(list)
        self._by_sector: dict[str, list[str]] = defaultdict(list)
        self._build_indexes()

    @classmethod
    def from_file(cls, path: Path) -> "GraphRepository":
        return cls(load_graph(path))

    def _build_indexes(self) -> None:
        for edge in self._data.edges:
            self._outgoing[edge.source].append(edge)
            self._incoming[edge.target].append(edge)
        for node in self._data.nodes.values():
            if not node.is_stock:
                continue
            if node.sector:
                self._by_sector[node.sector].append(node.id)
            for group in node.peer_groups:
                self._by_peer_group[group].append(node.id)

    # ---- node access -------------------------------------------------

    def get(self, node_id: str) -> Node | None:
        return self._data.nodes.get(node_id)

    def require(self, node_id: str) -> Node:
        node = self.get(node_id)
        if node is None:
            raise KeyError(f"unknown node: {node_id}")
        return node

    def nodes_of_type(self, node_type: NodeType) -> list[Node]:
        return [n for n in self._data.nodes.values() if n.type is node_type]

    def fo_symbols(self) -> list[str]:
        return sorted(n.id for n in self._data.nodes.values() if n.is_stock and n.fo)

    # ---- membership --------------------------------------------------

    def sector_members(self, sector: str) -> list[str]:
        return list(self._by_sector.get(_strip_sector_prefix(sector), []))

    def peer_group_members(self, group: str) -> list[str]:
        return list(self._by_peer_group.get(group, []))

    def peers_of(self, node_id: str) -> list[str]:
        """Every stock sharing at least one peer_group with `node_id`."""
        node = self.get(node_id)
        if node is None:
            return []
        peers = {
            member
            for group in node.peer_groups
            for member in self._by_peer_group.get(group, [])
        }
        peers.discard(node_id)
        return sorted(peers)

    # ---- edge access -------------------------------------------------

    def outgoing(self, node_id: str) -> list[Edge]:
        return list(self._outgoing.get(node_id, []))

    def incoming(self, node_id: str) -> list[Edge]:
        return list(self._incoming.get(node_id, []))

    def neighbours(self, node_id: str) -> list[Neighbour]:
        """All directly connected nodes, in both directions."""
        found: list[Neighbour] = []
        for edge in self._outgoing.get(node_id, []):
            if (node := self.get(edge.target)) is not None:
                found.append(Neighbour(node=node, edge=edge, outbound=True))
        for edge in self._incoming.get(node_id, []):
            if (node := self.get(edge.source)) is not None:
                found.append(Neighbour(node=node, edge=edge, outbound=False))
        return found

    # ---- stats -------------------------------------------------------

    @property
    def node_count(self) -> int:
        return len(self._data.nodes)

    @property
    def edge_count(self) -> int:
        return len(self._data.edges)


def _strip_sector_prefix(sector: str) -> str:
    return sector[len(SECTOR_PREFIX):] if sector.startswith(SECTOR_PREFIX) else sector
