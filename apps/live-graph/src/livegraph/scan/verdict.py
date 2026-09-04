"""Classify why a stock moved.

Pure arithmetic over evidence that is already gathered. The model narrates the
result but never computes it, so every verdict on screen can be checked against
the same numbers the UI shows.

The classification only ever answers "is this move shared or particular to this
name, and is there anything to account for it". It says nothing about whether
the move is right, and nothing about what happens next.
"""

from __future__ import annotations

import statistics

from .models import Evidence, GraphDriver, NewsScope, PeerMove, SectorContext, Verdict

#: Below this the stock is moving with its peers, so the move is not its own.
DEFAULT_GAP_THRESHOLD = 0.75
#: A fixed threshold alone is fragile: on a quiet session nothing ever clears
#: it, and on a volatile one everything does. A gap this many standard
#: deviations from the peer moves also counts as standing apart, which keeps
#: the scan useful across both.
DEFAULT_Z_THRESHOLD = 2.5
#: Fewer priced peers than this and the average is not worth trusting.
MIN_PEERS = 2
#: A standard deviation over fewer names than this is not worth dividing by.
MIN_PEERS_FOR_Z = 4
#: Floor on the peer spread. Rejecting tight clusters outright loses the very
#: cases the z-score exists for, but dividing by a near-zero spread manufactures
#: enormous scores, so the denominator is floored instead.
MIN_PEER_SPREAD = 0.15
#: Weak edges are ignored when looking for a contradiction; every stock has a
#: long tail of faint drivers and any of them can disagree by chance.
CONFLICT_MIN_STRENGTH = 0.5


def build_evidence(
    change_pct: float,
    peers: list[PeerMove],
    sector: SectorContext | None,
    drivers: list[GraphDriver],
    news_counts: dict[str, int],
) -> Evidence:
    peer_avg = _peer_average(peers)
    gap = None if peer_avg is None else change_pct - peer_avg
    return Evidence(
        change_pct=change_pct,
        peer_avg=peer_avg,
        peer_count=len(peers),
        gap=gap,
        sector=sector,
        peer_z=_peer_z(gap, peers),
        news_counts=dict(news_counts),
        conflicting_drivers=tuple(_contradicting(change_pct, drivers)),
    )


def classify(
    evidence: Evidence,
    gap_threshold: float = DEFAULT_GAP_THRESHOLD,
    z_threshold: float = DEFAULT_Z_THRESHOLD,
) -> Verdict:
    """Pick the verdict. Order matters: the first rule that fits wins."""
    if evidence.conflicting_drivers:
        return Verdict.CONFLICTED
    if not _stands_apart(evidence, gap_threshold, z_threshold):
        return Verdict.SECTOR_WIDE
    return Verdict.STOCK_SPECIFIC if evidence.has_news else Verdict.UNEXPLAINED


def _stands_apart(evidence: Evidence, gap_threshold: float, z_threshold: float) -> bool:
    """Is this move the stock's own, rather than one its neighbours share?

    Peers are the better comparator, so they are used whenever enough of them
    are priced. Either a large absolute gap or a large gap relative to how
    tightly the peers are clustered counts, so the scan still finds something
    on a quiet session and does not flag everything on a volatile one.

    Sector breadth is the fallback: in a sector where nearly everything moved
    the same way, no single member is standing apart.
    """
    if evidence.gap is not None and evidence.peer_count >= MIN_PEERS:
        if abs(evidence.gap) >= gap_threshold:
            return True
        return evidence.peer_z is not None and abs(evidence.peer_z) >= z_threshold

    sector = evidence.sector
    if sector is None:
        #: No comparator at all, so nothing can be called shared.
        return True
    if sector.is_one_sided and _same_direction(evidence.change_pct, sector.avg_change_pct):
        return False
    return abs(evidence.change_pct - sector.avg_change_pct) >= gap_threshold


def _contradicting(change_pct: float, drivers: list[GraphDriver]) -> list[GraphDriver]:
    """Drivers that are moving, and point the opposite way to the stock."""
    if change_pct == 0:
        return []
    stock_direction = 1 if change_pct > 0 else -1
    return [
        driver
        for driver in drivers
        if driver.strength >= CONFLICT_MIN_STRENGTH
        and driver.expected_direction != 0
        and driver.expected_direction != stock_direction
    ]


def _peer_z(gap: float | None, peers: list[PeerMove]) -> float | None:
    """Gap in peer standard deviations, with the spread floored. None if too few peers."""
    if gap is None or len(peers) < MIN_PEERS_FOR_Z:
        return None
    spread = max(statistics.pstdev(p.change_pct for p in peers), MIN_PEER_SPREAD)
    return gap / spread


def _peer_average(peers: list[PeerMove]) -> float | None:
    if len(peers) < MIN_PEERS:
        return None
    return statistics.fmean(p.change_pct for p in peers)


def _same_direction(a: float, b: float) -> bool:
    return (a > 0 and b > 0) or (a < 0 and b < 0)


def explain(symbol: str, evidence: Evidence, verdict: Verdict) -> str:
    """A plain sentence stating what the numbers say, with no interpretation."""
    gap = evidence.gap
    sector = evidence.sector

    if verdict is Verdict.CONFLICTED:
        driver = evidence.conflicting_drivers[0]
        return (
            f"{driver.node} is moving the other way to {symbol} through a "
            f"{driver.edge_type} edge, so the graph and the price disagree."
        )
    if verdict is Verdict.SECTOR_WIDE:
        if sector and sector.is_one_sided:
            #: Report whichever side actually dominates, not always advancers.
            rising = sector.advancing >= sector.declining
            count = sector.advancing if rising else sector.declining
            moved = "rose" if rising else "fell"
            return (
                f"{count} of {sector.breadth} priced {sector.name} names {moved} together. "
                f"Nothing here is specific to {symbol}."
            )
        return f"{symbol} is moving with its peers, so this is not its own move."
    if gap is None:
        return f"{symbol} has too few priced peers to compare against."

    direction = "ahead of" if gap > 0 else "behind"
    tail = (
        "and there is news to account for it"
        if verdict is Verdict.STOCK_SPECIFIC
        else "and nothing accounts for it"
    )
    return (
        f"{symbol} is {abs(gap):.2f}pp {direction} its peer group "
        f"across {evidence.peer_count} names, {tail}."
    )


def news_counts(scopes: list[NewsScope]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for scope in scopes:
        counts[str(scope)] = counts.get(str(scope), 0) + 1
    return counts
