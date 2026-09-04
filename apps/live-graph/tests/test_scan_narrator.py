"""Regressions guarded here:

Narration is the only per-stock model call in the scan, so its cache decides
both the bill and whether what you read is current:

- Opening the same stock again on the same day, with nothing changed, must not
  call the model a second time.
- A new headline, a materially shifted move, a reversal through zero, or a
  changed verdict must each force a rewrite. Missing any of these leaves a
  confident explanation on screen that no longer matches the numbers beside it.
- A tiny wobble across zero is not a reversal; treating it as one would
  regenerate all day on a stock sitting flat.
"""

import pytest

from livegraph.scan.models import (
    Evidence,
    GraphDriver,
    NewsScope,
    ScopedNews,
    SectorContext,
    StockScan,
    Verdict,
)
from livegraph.scan.narrator import Fingerprint, VerdictNarrator, brief, fingerprint_of, news_key

SECTOR = SectorContext(name="Financial services", avg_change_pct=0.76, advancing=53, declining=2)


def scan(symbol="CAMS", change=1.84, verdict=Verdict.UNEXPLAINED, news=(), drivers=()):
    evidence = Evidence(
        change_pct=change, peer_avg=0.74, peer_count=6, gap=change - 0.74,
        sector=SECTOR, peer_z=2.9, news_counts={}, conflicting_drivers=tuple(drivers),
    )
    return StockScan(
        symbol=symbol, name="Computer Age Management", sector=SECTOR.name,
        peer_groups=("FIN_MKTINFRA",), ltp=2856.04, change_pct=change,
        verdict=verdict, evidence=evidence, peers=(), drivers=(), news=tuple(news),
    )


def headline(title="Turnover hits a high", link="https://x.test/1", scope=NewsScope.SECTOR):
    return ScopedNews(scope=scope, title=title, source="Moneycontrol", ts=1.0, link=link)


class CountingNarrator(VerdictNarrator):
    """Counts model calls without making any."""

    def __init__(self):
        super().__init__(now=lambda: 1000.0)
        self.calls = 0

    async def _ask(self, scan):
        self.calls += 1
        return f"narration {self.calls}"


@pytest.fixture
def narrator():
    return CountingNarrator()


# ---- reuse -----------------------------------------------------------


async def test_first_look_calls_the_model(narrator):
    result = await narrator.narrate(scan())
    assert narrator.calls == 1
    assert result.refreshed_because == "first look"
    assert not result.from_cache


async def test_same_stock_same_day_unchanged_does_not_call_again(narrator):
    await narrator.narrate(scan())
    again = await narrator.narrate(scan())
    assert narrator.calls == 1
    assert again.from_cache
    assert again.text == "narration 1"


async def test_a_small_drift_does_not_trigger_a_rewrite(narrator):
    """Prices tick constantly; only a material shift is a different story."""
    await narrator.narrate(scan(change=1.84))
    await narrator.narrate(scan(change=1.61))
    await narrator.narrate(scan(change=2.10))
    assert narrator.calls == 1


# ---- invalidation ----------------------------------------------------


async def test_a_new_headline_forces_a_rewrite(narrator):
    await narrator.narrate(scan(news=[headline()]))
    result = await narrator.narrate(scan(news=[headline(), headline("New one", "https://x.test/2")]))
    assert narrator.calls == 2
    assert result.refreshed_because == "new headline"


async def test_a_material_shift_forces_a_rewrite(narrator):
    await narrator.narrate(scan(change=1.84))
    result = await narrator.narrate(scan(change=0.60))
    assert narrator.calls == 2
    assert result.refreshed_because == "move shifted materially"


async def test_a_reversal_through_zero_forces_a_rewrite(narrator):
    await narrator.narrate(scan(change=0.80))
    result = await narrator.narrate(scan(change=-0.40))
    assert narrator.calls == 2
    assert result.refreshed_because == "move reversed direction"


async def test_a_changed_verdict_forces_a_rewrite(narrator):
    """Explaining an anomaly must not survive the anomaly going away."""
    await narrator.narrate(scan(verdict=Verdict.UNEXPLAINED))
    result = await narrator.narrate(scan(verdict=Verdict.SECTOR_WIDE))
    assert narrator.calls == 2
    assert result.refreshed_because == "verdict changed"


async def test_a_new_day_forces_a_rewrite(narrator):
    await narrator.narrate(scan())
    stale = narrator.cached("CAMS")
    narrator._cache["CAMS"] = type(stale)(
        text=stale.text, written_at=stale.written_at,
        fingerprint=Fingerprint(day="1999-01-01", verdict=stale.fingerprint.verdict,
                                news_key=stale.fingerprint.news_key,
                                change_pct=stale.fingerprint.change_pct))
    result = await narrator.narrate(scan())
    assert narrator.calls == 2
    assert result.refreshed_because == "new trading day"


async def test_each_symbol_is_cached_separately(narrator):
    await narrator.narrate(scan(symbol="CAMS"))
    await narrator.narrate(scan(symbol="MCX"))
    await narrator.narrate(scan(symbol="CAMS"))
    assert narrator.calls == 2


# ---- fingerprint details --------------------------------------------


def test_headline_order_does_not_change_the_key():
    a, b = headline("A", "https://x/1"), headline("B", "https://x/2")
    assert news_key(scan(news=[a, b])) == news_key(scan(news=[b, a]))


def test_a_flat_stock_wobbling_across_zero_is_not_a_reversal():
    before = fingerprint_of(scan(change=0.10))
    after = fingerprint_of(scan(change=-0.12))
    assert before.superseded_by(after) is None


# ---- the brief the model receives -----------------------------------


def test_brief_carries_the_numbers_and_the_headlines():
    text = brief(scan(news=[headline("Turnover hits a high")]))
    assert "CAMS" in text and "+1.84%" in text
    assert "Unexplained" in text
    assert "6 priced names averaging +0.74%" in text
    assert "53 advancing and 2 declining" in text
    assert "Turnover hits a high" in text


def test_brief_says_plainly_when_there_is_no_news():
    assert "none found" in brief(scan())


def test_brief_names_a_conflicting_driver():
    driver = GraphDriver(edge_type="COST_INPUT", node="CRUDE", sign=-1, strength=0.8,
                         driver_change_pct=2.4)
    assert "CRUDE" in brief(scan(drivers=[driver]))


async def test_a_same_direction_shift_is_reported_as_a_shift_not_a_reversal(narrator):
    await narrator.narrate(scan(change=1.84))
    result = await narrator.narrate(scan(change=0.55))
    assert result.refreshed_because == "move shifted materially"
