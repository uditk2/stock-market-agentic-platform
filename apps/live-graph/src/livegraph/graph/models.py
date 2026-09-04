"""Typed view over the stock relationship graph. No I/O, no prices."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class NodeType(StrEnum):
    STOCK = "stock"
    SECTOR = "sector"
    MACRO = "macro"


class EdgeType(StrEnum):
    """How a source node's move translates to the target.

    Semantics are fixed by screener-graph-spec.md; see `propagates` for which
    of these are legal second-hop carriers.
    """

    COST_INPUT = "COST_INPUT"
    READ_THROUGH = "READ_THROUGH"
    DEMAND_DRIVER = "DEMAND_DRIVER"
    SUPPLIES = "SUPPLIES"
    PEER_OF = "PEER_OF"
    IN_SECTOR = "IN_SECTOR"


#: Edge types allowed to carry a second-hop impact. IN_SECTOR is membership
#: only, so blanket-propagating through a 500-member hub is never correct.
SECOND_HOP_TYPES: frozenset[EdgeType] = frozenset(
    {EdgeType.PEER_OF, EdgeType.SUPPLIES, EdgeType.READ_THROUGH}
)


@dataclass(frozen=True, slots=True)
class Node:
    id: str
    type: NodeType
    label: str
    name: str
    sector: str | None = None
    isin: str | None = None
    fo: bool = False
    tier: str | None = None
    peer_groups: tuple[str, ...] = ()

    @property
    def is_stock(self) -> bool:
        return self.type is NodeType.STOCK


@dataclass(frozen=True, slots=True)
class Edge:
    source: str
    target: str
    type: EdgeType
    strength: float
    sign: int
    note: str | None = None

    @property
    def propagates(self) -> bool:
        return self.type in SECOND_HOP_TYPES


@dataclass(frozen=True, slots=True)
class Neighbour:
    """One node reachable from a start node, with the edge that got us there."""

    node: Node
    edge: Edge
    outbound: bool


@dataclass(slots=True)
class GraphData:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
