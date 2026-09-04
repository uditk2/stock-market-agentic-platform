"""Regressions guarded here:

- Edge proposals must never surface a pair the graph already connects.
- Series must align on their common tail rather than being padded, which would
  invent observations that were never seen.
- A same-sector pair is marked low confidence, because shared index flow
  explains co-movement at least as well as any real relationship does.
"""

from livegraph.agent import CoMovementAnalyzer, PriceHistory


def _history(**series) -> PriceHistory:
    history = PriceHistory(window=500)
    for symbol, values in series.items():
        for value in values:
            history.record(symbol, value)
    return history


WAVE = [(-1) ** i * (i % 7) * 0.3 for i in range(80)]


def test_proposes_a_correlated_unconnected_pair():
    history = _history(AAA=WAVE[:60], BBB=[m * 1.02 for m in WAVE[:60]])
    analyzer = CoMovementAnalyzer(history, min_correlation=0.85, min_samples=30)

    proposals = analyzer.propose(has_edge=lambda a, b: False, same_sector=lambda a, b: False)
    assert len(proposals) == 1
    assert {proposals[0].source, proposals[0].target} == {"AAA", "BBB"}
    assert proposals[0].correlation > 0.99
    assert proposals[0].samples == 60


def test_never_proposes_a_pair_the_graph_already_connects():
    history = _history(AAA=WAVE[:60], BBB=[m * 1.02 for m in WAVE[:60]])
    analyzer = CoMovementAnalyzer(history, min_correlation=0.85, min_samples=30)
    assert analyzer.propose(has_edge=lambda a, b: True, same_sector=lambda a, b: False) == []


def test_short_series_is_not_proposed():
    history = _history(AAA=WAVE[:10], BBB=WAVE[:10])
    analyzer = CoMovementAnalyzer(history, min_correlation=0.5, min_samples=30)
    assert analyzer.propose(lambda a, b: False, lambda a, b: False) == []


def test_series_are_aligned_on_their_common_tail():
    """A symbol that started streaming later must not be zero-padded."""
    history = _history(AAA=WAVE, BBB=WAVE[-40:])
    analyzer = CoMovementAnalyzer(history, min_correlation=0.85, min_samples=30)

    proposals = analyzer.propose(lambda a, b: False, lambda a, b: False)
    assert proposals and proposals[0].samples == 40


def test_same_sector_pairs_are_marked_low_confidence():
    history = _history(AAA=WAVE, BBB=[m * 1.01 for m in WAVE])
    analyzer = CoMovementAnalyzer(history, min_correlation=0.85, min_samples=30)

    proposals = analyzer.propose(lambda a, b: False, same_sector=lambda a, b: True)
    assert proposals[0].same_sector
    assert proposals[0].confidence == "low"


def test_flat_series_yields_no_correlation():
    history = _history(AAA=[0.0] * 60, BBB=[0.0] * 60)
    analyzer = CoMovementAnalyzer(history, min_correlation=0.5, min_samples=30)
    assert analyzer.propose(lambda a, b: False, lambda a, b: False) == []


def test_history_window_bounds_memory():
    history = PriceHistory(window=10)
    for value in range(50):
        history.record("AAA", float(value))
    assert history.sample_count("AAA") == 10
    assert history.series("AAA")[0] == 40.0
