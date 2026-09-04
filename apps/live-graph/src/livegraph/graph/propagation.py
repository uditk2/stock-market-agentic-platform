"""Impact propagation over the graph, per screener-graph-spec.md section 4.

Direction is the trustworthy output. Magnitude is a heuristic, uncalibrated
score, so it is only ever meaningful as a relative ranking within one run.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Edge, EdgeType
from .repository import GraphRepository

#: Second-hop impacts are damped by this factor.
SECOND_HOP_ATTENUATION = 0.45


@dataclass(frozen=True, slots=True)
class Impact:
    node_id: str
    score: float
    hops: int
    path: tuple[str, ...]

    @property
    def direction(self) -> str:
        if self.score > 0:
            return "up"
        return "down" if self.score < 0 else "neutral"


class ImpactPropagator:
    def __init__(self, repo: GraphRepository, attenuation: float = SECOND_HOP_ATTENUATION):
        self._repo = repo
        self._attenuation = attenuation

    def propagate(self, origin: str, direction: int) -> list[Impact]:
        """Rank nodes affected by `origin` moving in `direction` (+1 / -1).

        Second-hop targets already hit directly are skipped, and only the
        strongest second-hop path per node is kept, so a large peer cluster
        cannot inflate its own members.
        """
        direct = self._direct_hop(origin, direction)
        second = self._second_hop(origin, direct)
        ranked = [*direct.values(), *second.values()]
        return sorted(ranked, key=lambda i: (-abs(i.score), i.node_id))

    def _direct_hop(self, origin: str, direction: int) -> dict[str, Impact]:
        impacts: dict[str, Impact] = {}
        for edge in self._traversable(origin):
            target = _other_end(edge, origin)
            score = direction * edge.sign * edge.strength
            if score == 0:
                continue
            impacts[target] = Impact(
                node_id=target, score=score, hops=1, path=(origin, target)
            )
        return impacts

    def _second_hop(self, origin: str, direct: dict[str, Impact]) -> dict[str, Impact]:
        impacts: dict[str, Impact] = {}
        for first in direct.values():
            for edge in self._traversable(first.node_id, propagating_only=True):
                target = _other_end(edge, first.node_id)
                if target == origin or target in direct:
                    continue
                score = first.score * edge.sign * edge.strength * self._attenuation
                if score == 0:
                    continue
                existing = impacts.get(target)
                if existing is not None and abs(existing.score) >= abs(score):
                    continue
                impacts[target] = Impact(
                    node_id=target,
                    score=score,
                    hops=2,
                    path=(origin, first.node_id, target),
                )
        return impacts

    def _traversable(self, node_id: str, propagating_only: bool = False) -> list[Edge]:
        """Edges usable for impact. IN_SECTOR is membership only, never a carrier."""
        edges = [
            edge
            for edge in (self._repo.outgoing(node_id) + self._repo.incoming(node_id))
            if edge.type is not EdgeType.IN_SECTOR
        ]
        if propagating_only:
            edges = [edge for edge in edges if edge.propagates]
        return edges


def _other_end(edge: Edge, node_id: str) -> str:
    return edge.target if edge.source == node_id else edge.source
