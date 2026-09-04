"""Agent narration of a verdict, recomputed only when something actually changed.

The deterministic classifier already decides what the verdict is. The model's
job is only to read the evidence and the headlines and say why, in a sentence
or two a person can act on.

Model calls are the expensive part, so a narration is reused for the rest of
the trading day unless one of the things it was based on has moved:

  - a new headline arrived for the stock
  - the move reversed or changed materially since it was written
  - the deterministic verdict itself changed class
  - it is a different trading day

Anything else is the same stock, the same story, and the same answer.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from ..llm import build_analyst_model
from .models import StockScan, VERDICT_LABEL

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")
#: A move that has shifted this far since the narration was written is a
#: different story, even with no new headline.
REVERSAL_PCT = 1.0

INSTRUCTIONS = """\
You explain why one Indian F&O stock is moving, for a trader scanning the day.

The verdict and every number below were computed before you were called. Do not
recompute, contradict, or restate them at length. Explain in at most three
sentences what they mean together, and say plainly when the evidence is thin.

Rules:
- Use only the figures and headlines given. Never introduce a price, a
  percentage, or a headline that is not below.
- Name the strongest piece of evidence first.
- If the verdict is "Unexplained", say what is missing rather than speculating
  about a cause.
- No price targets, no predictions, no advice.
"""


@dataclass(frozen=True, slots=True)
class Fingerprint:
    """What a narration was based on. If this changes, the narration is stale."""

    day: str
    verdict: str
    news_key: str
    change_pct: float

    def superseded_by(self, other: "Fingerprint") -> str | None:
        """Why `other` needs a fresh narration, or None if it does not."""
        if self.day != other.day:
            return "new trading day"
        if self.verdict != other.verdict:
            return "verdict changed"
        if self.news_key != other.news_key:
            return "new headline"
        #: Reversal is checked first: a move that crossed zero is usually also a
        #: large shift, and "reversed" is the more useful of the two reasons.
        if _crossed_zero(self.change_pct, other.change_pct):
            return "move reversed direction"
        if abs(other.change_pct - self.change_pct) >= REVERSAL_PCT:
            return "move shifted materially"
        return None


@dataclass(frozen=True, slots=True)
class Narration:
    text: str
    written_at: float
    fingerprint: Fingerprint
    #: Why it was regenerated, or None when it was served from cache.
    refreshed_because: str | None = None
    from_cache: bool = False


class VerdictNarrator:
    def __init__(self, model=None, now=None):
        self._model = model
        self._agent = None
        self._cache: dict[str, Narration] = {}
        self._now = now or _epoch_now

    async def narrate(self, scan: StockScan) -> Narration:
        current = fingerprint_of(scan)
        cached = self._cache.get(scan.symbol)

        if cached is not None:
            reason = cached.fingerprint.superseded_by(current)
            if reason is None:
                return Narration(
                    text=cached.text,
                    written_at=cached.written_at,
                    fingerprint=cached.fingerprint,
                    from_cache=True,
                )
        else:
            reason = "first look"

        text = await self._ask(scan)
        fresh = Narration(
            text=text, written_at=self._now(), fingerprint=current, refreshed_because=reason
        )
        self._cache[scan.symbol] = fresh
        logger.info("narrated %s (%s)", scan.symbol, reason)
        return fresh

    def cached(self, symbol: str) -> Narration | None:
        return self._cache.get(symbol)

    def clear(self) -> None:
        self._cache.clear()

    async def _ask(self, scan: StockScan) -> str:
        from pydantic_ai import Agent

        if self._agent is None:
            self._agent = Agent(self._model or build_analyst_model(), retries=1)
        #: Instructions ride in the user message: the Claude backend behind
        #: CLIProxyAPI discards the system prompt.
        result = await self._agent.run(f"{INSTRUCTIONS}\n\n{brief(scan)}")
        return result.output.strip()


def fingerprint_of(scan: StockScan) -> Fingerprint:
    return Fingerprint(
        day=trading_day(),
        verdict=str(scan.verdict),
        news_key=news_key(scan),
        change_pct=scan.change_pct,
    )


def trading_day() -> str:
    return datetime.now(IST).date().isoformat()


def news_key(scan: StockScan) -> str:
    """Stable over the same headlines in any order, changes when one arrives."""
    identity = sorted(f"{n.scope}:{n.link or n.title}" for n in scan.news)
    return hashlib.sha1("|".join(identity).encode("utf-8")).hexdigest()[:16]


def brief(scan: StockScan) -> str:
    """Everything the model may use, and nothing else."""
    e = scan.evidence
    lines = [
        f"Stock: {scan.symbol} ({scan.name}), sector {scan.sector or 'unknown'}",
        f"Move today: {scan.change_pct:+.2f}%",
        f"Verdict (already decided): {VERDICT_LABEL[scan.verdict]}",
    ]
    if e.peer_avg is not None:
        lines.append(
            f"Peer group: {e.peer_count} priced names averaging {e.peer_avg:+.2f}%, "
            f"gap {e.gap:+.2f}pp"
        )
    else:
        lines.append(f"Peer group: only {e.peer_count} priced peers, too few to compare")
    if e.sector:
        lines.append(
            f"Sector {e.sector.name}: {e.sector.avg_change_pct:+.2f}% average, "
            f"{e.sector.advancing} advancing and {e.sector.declining} declining"
        )
    if e.conflicting_drivers:
        lines.append("Drivers pointing the other way: " + ", ".join(
            f"{d.node} ({d.edge_type}, sign {d.sign:+d}, moved {d.driver_change_pct:+.2f}%)"
            for d in e.conflicting_drivers))

    lines.append("")
    if scan.news:
        lines.append("Headlines:")
        lines += [f"  [{n.scope}] {n.title} ({n.source})" for n in scan.news]
    else:
        lines.append("Headlines: none found for this stock, its sector, or the market.")
    return "\n".join(lines)


def _crossed_zero(before: float, after: float) -> bool:
    """A reversal only counts if both sides are more than noise."""
    if abs(before) < 0.25 or abs(after) < 0.25:
        return False
    return (before > 0) != (after > 0)


def _epoch_now() -> float:
    import time

    return time.time()
