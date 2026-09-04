"""Regressions guarded here:

- A futures trading symbol must reduce to the bare underlying, else no tick
  ever matches a graph node and the whole overlay is silently empty.
- Nearest-expiry selection must keep exactly one contract per underlying;
  keeping all series multiplies the subscription count by the number of
  monthlies and trips the broker's cap.
- Depth/heartbeat frames carry no LTP and must be dropped, not emitted as 0.0,
  which would render as a stock crashing to zero.
"""

import pytest

from livegraph.feed import (
    Instrument,
    Segment,
    TickNormalizer,
    extract_underlying,
    nearest_expiry_per_underlying,
    parse_instruments,
)


@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("RELIANCE25SEPFUT", "RELIANCE"),
        ("HDFCBANK25OCTFUT", "HDFCBANK"),
        ("M&M25SEPFUT", "M&M"),
        ("NIFTY25SEP25000CE", "NIFTY"),
        ("BANKNIFTY25SEP52000PE", "BANKNIFTY"),
        ("INFY", "INFY"),
    ],
)
def test_extract_underlying(symbol, expected):
    assert extract_underlying(symbol) == expected


def test_parse_instruments_skips_non_futures_in_fno():
    rows = [
        {"pSymbol": "1", "pTrdSymbol": "RELIANCE25SEPFUT", "pLotSize": "500", "pExpiryDate": "25-09-2025"},
        {"pSymbol": "2", "pTrdSymbol": "RELIANCE25SEP1400CE", "pLotSize": "500"},
        {"pSymbol": "3", "pTrdSymbol": "", "pLotSize": "500"},
    ]
    parsed = parse_instruments(rows, Segment.FNO)
    assert [i.trading_symbol for i in parsed] == ["RELIANCE25SEPFUT"]
    assert parsed[0].underlying == "RELIANCE"
    assert parsed[0].lot_size == 500
    assert parsed[0].expiry == "2025-09-25"


def test_nearest_expiry_keeps_one_contract_per_underlying():
    instruments = [
        Instrument("1", Segment.FNO, "RELIANCE25OCTFUT", "RELIANCE", expiry="2025-10-30"),
        Instrument("2", Segment.FNO, "RELIANCE25SEPFUT", "RELIANCE", expiry="2025-09-25"),
        Instrument("3", Segment.FNO, "INFY25SEPFUT", "INFY", expiry="2025-09-25"),
    ]
    kept = nearest_expiry_per_underlying(instruments)
    assert [i.trading_symbol for i in kept] == ["INFY25SEPFUT", "RELIANCE25SEPFUT"]


def test_undated_contract_loses_to_a_dated_one():
    instruments = [
        Instrument("1", Segment.FNO, "INFY25SEPFUT", "INFY", expiry=None),
        Instrument("2", Segment.FNO, "INFY25OCTFUT", "INFY", expiry="2025-10-30"),
    ]
    assert nearest_expiry_per_underlying(instruments)[0].instrument_token == "2"


@pytest.fixture
def normalizer():
    return TickNormalizer(
        {
            "11536": Instrument("11536", Segment.FNO, "RELIANCE25SEPFUT", "RELIANCE"),
            "1594": Instrument("1594", Segment.CASH, "INFY", "INFY"),
        }
    )


def test_normalizes_compact_socket_keys(normalizer):
    ticks = normalizer.normalize_message(
        [{"tk": "11536", "ltp": "1425.50", "nc": "1.24", "oi": "12000", "v": "9500", "ft": "1725441000"}]
    )
    assert len(ticks) == 1
    tick = ticks[0]
    assert tick.underlying == "RELIANCE"
    assert tick.ltp == 1425.50
    assert tick.change_pct == 1.24
    assert tick.open_interest == 12000
    assert tick.is_futures


def test_normalizes_long_rest_keys(normalizer):
    ticks = normalizer.normalize_message(
        {"instrument_token": "1594", "last_traded_price": 1500.0, "volume": 100}
    )
    assert ticks[0].underlying == "INFY"
    assert ticks[0].segment is Segment.CASH


def test_frame_without_ltp_is_dropped(normalizer):
    """A depth-only frame must not surface as a zero price."""
    assert normalizer.normalize_message({"tk": "11536", "oi": "12000"}) == []


def test_unknown_token_is_dropped(normalizer):
    assert normalizer.normalize_message({"tk": "99999", "ltp": 100.0}) == []


def test_falls_back_to_trading_symbol_when_token_unknown(normalizer):
    ticks = normalizer.normalize_message({"ts": "RELIANCE25SEPFUT", "ltp": 1400.0})
    assert ticks[0].underlying == "RELIANCE"
