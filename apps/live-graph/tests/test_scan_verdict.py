"""Regressions guarded here:

The verdict is the one number-derived judgement the UI shows, so it has to be
right for the reasons stated, not by luck:

- An unpriced peer must be absent from the average, never counted as zero.
  Treating it as zero drags the peer average toward nothing and turns ordinary
  sector moves into false "unexplained" flags, which is exactly the noise the
  scan exists to remove.
- A one-sided sector must explain its members even when a stock has too few
  priced peers to compare against, otherwise every thinly-covered name in a
  sector-wide selloff reads as an anomaly.
- Only a driver that is actually moving, and is strong enough to matter, can
  make a move "conflicted". Flat or faint drivers must not.
- "Stock-specific" requires stock-level or web news. Sector and market
  headlines are context, not an explanation for one name standing apart.
"""

import pytest

from livegraph.scan import Verdict, build_evidence, classify, explain
from livegraph.scan.models import GraphDriver, NewsScope, PeerMove, SectorContext
from livegraph.scan.verdict import news_counts

FLAT_SECTOR = SectorContext(name="IT", avg_change_pct=0.1, advancing=6, declining=5)
ONE_SIDED = SectorContext(name="Power", avg_change_pct=-1.39, advancing=0, declining=8)


def ev(change, peers=(), sector=FLAT_SECTOR, drivers=(), news=None):
    return build_evidence(
        change_pct=change,
        peers=[PeerMove(s, c) for s, c in peers],
        sector=sector,
        drivers=list(drivers),
        news_counts=news or {},
    )


# ---- standing apart from peers --------------------------------------


def test_moving_with_peers_is_sector_wide():
    e = ev(1.51, peers=[("HDFCBANK", 1.31), ("ICICIBANK", 1.24), ("AXISBANK", 1.18)])
    assert classify(e) is Verdict.SECTOR_WIDE


def test_standing_apart_without_news_is_unexplained():
    e = ev(1.84, peers=[("MCX", 0.31), ("BSE", 0.34), ("CDSL", 0.29)])
    assert classify(e) is Verdict.UNEXPLAINED


def test_standing_apart_with_stock_news_is_stock_specific():
    e = ev(1.57, peers=[("BLUEDART", 0.4), ("TCI", 0.3)], news={"stock": 1})
    assert classify(e) is Verdict.STOCK_SPECIFIC


def test_web_news_also_explains_a_move():
    """The web fallback is weaker evidence but it is still evidence."""
    e = ev(-0.83, peers=[("TATASTEEL", 0.62), ("JSWSTEEL", 0.55)], news={"web": 1})
    assert classify(e) is Verdict.STOCK_SPECIFIC


def test_sector_and_market_news_do_not_explain_a_divergence():
    """A market round-up says nothing about why one name broke away."""
    e = ev(1.84, peers=[("MCX", 0.31), ("BSE", 0.34)], news={"sector": 2, "market": 3})
    assert classify(e) is Verdict.UNEXPLAINED


# ---- unpriced peers --------------------------------------------------


def test_unpriced_peers_are_excluded_not_zeroed():
    """Only two peers are priced, and the stock is in line with both."""
    e = ev(1.20, peers=[("A", 1.15), ("B", 1.10)])
    assert e.peer_count == 2
    assert e.peer_avg == pytest.approx(1.125)
    assert classify(e) is Verdict.SECTOR_WIDE


def test_too_few_priced_peers_falls_back_to_the_sector():
    e = ev(-1.5, peers=[("ONLYONE", -1.4)], sector=ONE_SIDED)
    assert e.peer_avg is None
    assert classify(e) is Verdict.SECTOR_WIDE


def test_one_sided_sector_explains_a_thinly_covered_name():
    e = ev(-1.77, peers=[], sector=ONE_SIDED)
    assert classify(e) is Verdict.SECTOR_WIDE


def test_moving_against_a_one_sided_sector_still_stands_apart():
    e = ev(1.40, peers=[], sector=ONE_SIDED)
    assert classify(e) is Verdict.UNEXPLAINED


def test_no_comparator_at_all_cannot_be_called_shared():
    e = ev(2.0, peers=[], sector=None)
    assert classify(e) is Verdict.UNEXPLAINED


# ---- conflicting drivers --------------------------------------------


def driver(node, sign, strength, moved):
    return GraphDriver(edge_type="COST_INPUT", node=node, sign=sign, strength=strength,
                       driver_change_pct=moved)


def test_a_moving_driver_pointing_the_other_way_is_conflicted():
    """Crude up through a negative cost edge should push the stock down."""
    e = ev(1.2, peers=[("A", 1.1), ("B", 1.15)], drivers=[driver("CRUDE", -1, 0.8, 2.0)])
    assert classify(e) is Verdict.CONFLICTED
    assert e.conflicting_drivers[0].node == "CRUDE"


def test_a_driver_pointing_the_same_way_is_not_a_conflict():
    e = ev(-1.2, peers=[("A", -1.1), ("B", -1.15)], drivers=[driver("CRUDE", -1, 0.8, 2.0)])
    assert classify(e) is Verdict.SECTOR_WIDE


def test_a_flat_driver_cannot_conflict():
    e = ev(1.2, peers=[("A", 1.1), ("B", 1.15)], drivers=[driver("CRUDE", -1, 0.8, 0.0)])
    assert not e.conflicting_drivers


def test_an_unpriced_driver_cannot_conflict():
    e = ev(1.2, peers=[("A", 1.1), ("B", 1.15)], drivers=[driver("CRUDE", -1, 0.8, None)])
    assert not e.conflicting_drivers


def test_a_faint_driver_cannot_conflict():
    """Every stock has a tail of weak edges; any of them can disagree by chance."""
    e = ev(1.2, peers=[("A", 1.1), ("B", 1.15)], drivers=[driver("CRUDE", -1, 0.2, 2.0)])
    assert not e.conflicting_drivers
    assert classify(e) is Verdict.SECTOR_WIDE


def test_conflict_outranks_everything_else():
    e = ev(1.84, peers=[("A", 0.1)], news={"stock": 3}, drivers=[driver("CRUDE", -1, 0.9, 3.0)])
    assert classify(e) is Verdict.CONFLICTED


# ---- explanation -----------------------------------------------------


def test_explanation_states_the_gap_and_the_peer_count():
    e = ev(1.84, peers=[("MCX", 0.31), ("BSE", 0.34)])
    text = explain("CAMS", e, classify(e))
    assert "CAMS" in text and "pp" in text and "2 names" in text
    assert "nothing accounts for it" in text


def test_sector_explanation_reports_the_side_that_actually_moved():
    """A falling sector must not be described as "0 of 8 moved the same way"."""
    e = ev(-1.77, peers=[], sector=ONE_SIDED)
    text = explain("TATAPOWER", e, classify(e))
    assert "8 of 8 priced Power names fell together" in text

    rising = SectorContext(name="FMCG", avg_change_pct=0.79, advancing=14, declining=0)
    up = ev(1.2, peers=[], sector=rising)
    assert "14 of 14 priced FMCG names rose together" in explain("VBL", up, classify(up))


def test_conflict_explanation_names_the_driver():
    e = ev(1.2, peers=[("A", 1.1), ("B", 1.15)], drivers=[driver("CRUDE", -1, 0.8, 2.0)])
    assert "CRUDE" in explain("MRF", e, classify(e))


def test_news_counts_tally_by_scope():
    counts = news_counts([NewsScope.STOCK, NewsScope.SECTOR, NewsScope.SECTOR])
    assert counts == {"stock": 1, "sector": 2}


# ---- adaptive threshold ---------------------------------------------


def test_a_tight_peer_group_flags_a_small_but_unusual_gap():
    """On a quiet session a fixed threshold never fires and the scan goes blind.

    These peers are clustered within 0.06pp, so a 0.4pp gap is far outside
    them even though it is well under the absolute threshold.
    """
    peers = [("A", 1.00), ("B", 1.03), ("C", 0.97), ("D", 1.02), ("E", 0.98)]
    e = ev(1.40, peers=peers)
    assert abs(e.gap) < 0.75, "this test is only meaningful below the absolute threshold"
    assert e.peer_z is not None and abs(e.peer_z) > 2.5
    assert classify(e) is Verdict.UNEXPLAINED


def test_a_scattered_peer_group_does_not_flag_the_same_gap():
    """The identical gap, against peers that are all over the place, is normal."""
    peers = [("A", 2.10), ("B", -0.30), ("C", 1.40), ("D", 0.20), ("E", 1.60)]
    e = ev(1.40, peers=peers)
    assert abs(e.gap) < 0.75
    assert abs(e.peer_z) < 2.5
    assert classify(e) is Verdict.SECTOR_WIDE


def test_z_needs_enough_peers_to_mean_anything():
    e = ev(1.40, peers=[("A", 1.00), ("B", 1.02)])
    assert e.peer_z is None
    assert classify(e) is Verdict.SECTOR_WIDE


def test_identical_peers_do_not_manufacture_an_infinite_score():
    """A zero spread is floored, so the score stays finite and interpretable."""
    e = ev(1.40, peers=[("A", 1.0), ("B", 1.0), ("C", 1.0), ("D", 1.0)])
    assert e.peer_z is not None
    assert abs(e.peer_z) < 10, "a floored spread must not produce a runaway z"
    #: Four peers all at exactly 1.0 while the stock did 1.4 is standing apart.
    assert classify(e) is Verdict.UNEXPLAINED
