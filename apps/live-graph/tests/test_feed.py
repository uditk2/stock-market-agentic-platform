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


# ---- the envelope Kotak actually sends -------------------------------
#
# Not a bare quote: `{"type": ..., "data": [...]}`. Parsing the envelope finds
# no `ltp` on it and drops the frame, so a fully working session — logged in,
# socket open, tokens subscribed — delivered no price at all and said nothing
# beyond "frame produced no tick".


def test_quotes_inside_an_envelope_are_read(normalizer):
    ticks = normalizer.normalize_message(
        {"type": "quote", "data": [{"tk": "11536", "ltp": "1425.50"}, {"tk": "1594", "ltp": "1500"}]}
    )
    assert [t.underlying for t in ticks] == ["RELIANCE", "INFY"]


def test_a_single_quote_in_an_envelope_is_read(normalizer):
    ticks = normalizer.normalize_message({"type": "quote", "data": {"tk": "1594", "ltp": "1500"}})
    assert ticks[0].underlying == "INFY"


def test_an_envelope_carrying_no_quotes_is_quiet(normalizer):
    assert normalizer.normalize_message({"type": "heartbeat", "data": []}) == []


def test_a_quote_that_carries_its_own_price_is_not_unwrapped(normalizer):
    """`data` on a priced dict is that quote's payload, not an envelope around it."""
    ticks = normalizer.normalize_message({"tk": "11536", "ltp": "1425.50", "data": "anything"})
    assert ticks[0].ltp == 1425.50


def test_a_supplied_totp_makes_the_stored_secret_unnecessary():
    """The secret is only there to derive a code unattended.

    Someone reading the six digits off their authenticator has supplied the
    thing the secret would have produced, so demanding the secret as well would
    block the one login path that needs no stored secret at all.
    """
    from livegraph.feed import KotakSession
    from livegraph.feed.config import KotakSettings

    settings = KotakSettings(
        consumer_key="k", mobile_number="+919876543210", ucc="ABC12", mpin="1234",
        totp_secret="",
    )
    calls = {}

    class StubClient:
        def totp_login(self, **kwargs):
            calls.update(kwargs)
            return {"data": {"token": "view"}}

        def totp_validate(self, **kwargs):
            return {"data": {"token": "trade"}}

    session = KotakSession(settings, client_factory=lambda _: StubClient())
    session.login(totp="123456")

    assert calls["totp"] == "123456"
    assert session.is_active


def test_without_a_secret_or_a_code_the_login_still_refuses():
    from livegraph.feed import KotakAuthError, KotakSession
    from livegraph.feed.config import KotakSettings

    settings = KotakSettings(
        consumer_key="k", mobile_number="+919876543210", ucc="ABC12", mpin="1234",
        totp_secret="",
    )
    session = KotakSession(settings, client_factory=lambda _: object())
    with pytest.raises(KotakAuthError, match="totp_secret"):
        session.login()


# ---- scrip master ----------------------------------------------------
#
# `NeoAPI.scrip_master(exchange_segment=...)` returns a URL to a CSV, not rows.
# Feeding that to the row parser iterated the characters of a URL and failed
# with "'str' object has no attribute 'get'" — a message that says nothing
# about the actual mistake, which is why each shape is pinned here.


def test_a_url_is_downloaded_and_read_as_rows():
    from unittest import mock

    from livegraph.feed import load_scrip_master

    csv_text = (
        "pSymbol,pTrdSymbol,lLotSize,pExpiryDate\n"
        "35001,RELIANCE25SEPFUT,500,25-09-2026\n"
    )

    class Response:
        def read(self): return csv_text.encode()
        def __enter__(self): return self
        def __exit__(self, *args): return False

    with mock.patch("urllib.request.urlopen", return_value=Response()):
        rows = load_scrip_master("https://example.test/nse_fo.csv")

    assert rows == [{
        "pSymbol": "35001", "pTrdSymbol": "RELIANCE25SEPFUT",
        "lLotSize": "500", "pExpiryDate": "25-09-2026",
    }]


def test_rows_are_passed_through_unchanged():
    from livegraph.feed import load_scrip_master

    rows = [{"pSymbol": "1", "pTrdSymbol": "INFY25SEPFUT"}]
    assert load_scrip_master(rows) is rows


def test_the_sdk_error_dict_becomes_a_readable_failure():
    """The SDK returns errors instead of raising, in three different spellings."""
    from livegraph.feed import ScripMasterError, load_scrip_master

    for payload, expected in (
        ({"Error Message": "Complete the 2fa process"}, "2fa"),
        ({"Error": "Exchange Segment is not available"}, "Exchange Segment"),
        ({"error": "boom"}, "boom"),
    ):
        with pytest.raises(ScripMasterError, match=expected):
            load_scrip_master(payload)


def test_a_list_of_strings_is_caught_here_not_deep_in_the_parser():
    from livegraph.feed import ScripMasterError, load_scrip_master

    with pytest.raises(ScripMasterError, match="list of str"):
        load_scrip_master(["https://example.test/a.csv"])


def test_something_that_is_not_a_url_is_refused_before_the_network():
    from livegraph.feed import ScripMasterError, load_scrip_master

    with pytest.raises(ScripMasterError, match="not a URL"):
        load_scrip_master("/tmp/local/path.csv")


def test_the_csv_column_names_kotak_actually_uses_are_parsed():
    """The CSV says lLotSize and lExpiryDate; the JSON endpoints say pLotSize.

    Only the p-spellings were known, so every contract came back with no lot
    size and no expiry, and "nearest expiry" then picked an arbitrary contract.
    """
    rows = [{
        "pSymbol": "35001",
        "pTrdSymbol": "RELIANCE25SEPFUT",
        "lLotSize": "500",
        "pExpiryDate": "25-09-2026",
    }]
    parsed = parse_instruments(rows, Segment.FNO)
    assert parsed[0].lot_size == 500
    assert parsed[0].expiry == "2026-09-25"


# ---- the mobile number Kotak will accept -----------------------------
#
# `totp_login` validates `mobileNumber` as a field before it checks the
# credentials behind it, and refuses the spelling it does not want with
# "Invalid field 'MobileNumber'; must be a valid mobile number" — the same
# failure a wrong number gives, from a number that is entirely correct. The
# login therefore carries every spelling of the same ten digits rather than
# asking an operator to guess which one their broker wants today.


@pytest.mark.parametrize(
    "typed",
    ["+919876543210", "919876543210", "9876543210", "09876543210",
     "+91 98765 43210", "+91-98765-43210"],
)
def test_every_way_of_writing_one_number_yields_the_same_spellings(typed):
    from livegraph.feed.config import mobile_spellings

    assert mobile_spellings(typed) == ("+919876543210", "919876543210", "9876543210")


@pytest.mark.parametrize("typed", ["", "98765", "not a number", "+1 555 0100"])
def test_an_unreadable_number_is_passed_through_untouched(typed):
    """Kotak's own words are more use than a guess this module invented."""
    from livegraph.feed.config import mobile_spellings

    assert mobile_spellings(typed) == (typed.strip(),)


def _settings_with_mobile(value: str):
    from livegraph.feed.config import KotakSettings

    return KotakSettings(
        consumer_key="k", mobile_number=value, ucc="ABC12", mpin="1234", totp_secret="",
    )


class _PickyClient:
    """Kotak, refusing every spelling of the number but one."""

    REJECTION = {"error": [{"code": "400", "message": "Invalid field 'MobileNumber'"}]}

    def __init__(self, accepts: str):
        self.accepts = accepts
        self.tried: list[str] = []

    def totp_login(self, mobile_number=None, **kwargs):
        self.tried.append(mobile_number)
        if mobile_number != self.accepts:
            return dict(self.REJECTION)
        return {"data": {"token": "view"}}

    def totp_validate(self, **kwargs):
        return {"data": {"token": "trade"}}


@pytest.mark.parametrize("accepted", ["+919876543210", "919876543210", "9876543210"])
def test_login_finds_the_spelling_kotak_wants(accepted):
    from livegraph.feed import KotakSession

    client = _PickyClient(accepts=accepted)
    session = KotakSession(_settings_with_mobile("+919876543210"), client_factory=lambda _: client)
    session.login(totp="123456")

    assert session.is_active
    assert client.tried[-1] == accepted
    #: It stops at the first one that works rather than trying them all.
    assert accepted not in client.tried[:-1]


def test_a_number_refused_in_every_form_says_so():
    """Once the format is ruled out, what is left is the digits or the UCC."""
    from livegraph.feed import KotakAuthError, KotakSession

    client = _PickyClient(accepts="nothing at all")
    session = KotakSession(_settings_with_mobile("+919876543210"), client_factory=lambda _: client)
    with pytest.raises(KotakAuthError, match="every form"):
        session.login(totp="123456")

    assert len(client.tried) == 3


def test_an_error_that_is_not_about_the_mobile_number_is_not_retried():
    """A wrong TOTP must fail once, not three times against a live endpoint."""
    from livegraph.feed import KotakAuthError, KotakSession

    class WrongTotp:
        def __init__(self):
            self.calls = 0

        def totp_login(self, **kwargs):
            self.calls += 1
            return {"error": [{"code": "401", "message": "Invalid TOTP"}]}

    client = WrongTotp()
    session = KotakSession(_settings_with_mobile("+919876543210"), client_factory=lambda _: client)
    with pytest.raises(KotakAuthError, match="Invalid TOTP"):
        session.login(totp="123456")

    assert client.calls == 1


def test_every_spelling_refused_does_not_blame_the_number(monkeypatch):
    """Measured against the live API: a well-formed number reaches the code check.

    A malformed number is refused on the field; a well-formed one gets as far
    as the TOTP and comes back "Invalid TOTP". So a well-formed number refused
    on the field is something other than its spelling — most often a burst of
    attempts — and telling someone to correct a value that is already right
    sends them to change the one thing that is not wrong.
    """
    from livegraph.feed import KotakAuthError, KotakSession
    from livegraph.feed.config import KotakSettings

    monkeypatch.setattr("livegraph.feed.session._RETRY_PAUSE_SECONDS", 0)
    settings = KotakSettings(
        consumer_key="k", mobile_number="+919876543210", ucc="ABC12", mpin="1234",
        totp_secret="JBSWY3DPEHPK3PXP",
    )

    attempts = []

    class Refusing:
        def totp_login(self, **kwargs):
            attempts.append(kwargs["mobile_number"])
            return {"error": [{"message": "Invalid field 'MobileNumber'; must be valid"}]}

    session = KotakSession(settings, client_factory=lambda _: Refusing())
    with pytest.raises(KotakAuthError) as caught:
        session.login(totp="123456")

    message = str(caught.value)
    assert attempts == ["+919876543210", "919876543210", "9876543210"]
    assert "too many attempts" in message
    assert "wrong number for this UCC" in message
    #: The old wording told the operator to go and check the number, full stop.
    assert "Check it is the number registered" not in message


def test_a_rejection_that_is_not_about_the_mobile_field_is_raised_at_once():
    """A wrong code must not cost three attempts and three explanations."""
    from livegraph.feed import KotakAuthError, KotakSession
    from livegraph.feed.config import KotakSettings

    settings = KotakSettings(
        consumer_key="k", mobile_number="+919876543210", ucc="ABC12", mpin="1234",
        totp_secret="JBSWY3DPEHPK3PXP",
    )
    calls = []

    class WrongCode:
        def totp_login(self, **kwargs):
            calls.append(kwargs)
            return {"error": [{"code": "10506", "message": "Invalid TOTP"}]}

    session = KotakSession(settings, client_factory=lambda _: WrongCode())
    with pytest.raises(KotakAuthError, match="Invalid TOTP"):
        session.login(totp="000000")
    assert len(calls) == 1


# ---- what the change percentage is measured against --------------------


def test_previous_close_is_never_mistaken_for_the_last_price():
    """`c` is the previous day's close in Kotak's socket protocol.

    It was in the last-price key list, so a partial frame carrying `c` and no
    `ltp` — Kotak sends only what changed — would have been published as a live
    price. A stale price that looks live is worse than a missing one.
    """
    from livegraph.feed import Instrument, Segment, TickNormalizer

    index = {"11536": Instrument("11536", Segment.FNO, "RELIANCE25SEPFUT", "RELIANCE")}
    normalizer = TickNormalizer(index)

    assert normalizer.normalize_one({"tk": "11536", "c": "2400"}) is None

    tick = normalizer.normalize_one(
        {"tk": "11536", "ltp": "2500", "c": "2400", "op": "2450", "nc": "4.17"}
    )
    assert tick.ltp == 2500.0
    assert tick.prev_close == 2400.0
    assert tick.day_open == 2450.0


def test_the_baseline_of_a_change_percentage_can_be_checked():
    """The app forwards Kotak's percentage rather than computing one.

    Carrying both baselines makes the convention measurable instead of assumed:
    4.17% off 2400 is the previous close, not the 2450 open.
    """
    from livegraph.feed import Instrument, Segment, TickNormalizer

    index = {"11536": Instrument("11536", Segment.FNO, "RELIANCE25SEPFUT", "RELIANCE")}
    tick = TickNormalizer(index).normalize_one(
        {"tk": "11536", "ltp": "2500", "c": "2400", "op": "2450", "nc": "4.17"}
    )

    from_close = (tick.ltp - tick.prev_close) / tick.prev_close * 100
    from_open = (tick.ltp - tick.day_open) / tick.day_open * 100
    assert round(from_close, 2) == tick.change_pct
    assert round(from_open, 2) != tick.change_pct


def test_a_frame_that_matches_nothing_is_counted_not_swallowed():
    """"No prices" has three causes that look identical from outside.

    A silent socket, frames carrying no price, and frames for tokens this
    stream never subscribed to all end as an empty screen. Counting them apart
    is the difference between diagnosing and guessing.
    """
    from livegraph.feed import Instrument, Segment, TickStream

    known = Instrument("11536", Segment.FNO, "RELIANCE25SEPFUT", "RELIANCE")
    stream = TickStream(client=object(), instruments=[known])

    stream._on_message({"tk": "99999", "ltp": "100"})   # not subscribed
    stream._on_message({"tk": "11536"})                  # no price in the frame
    assert stream.frames_received == 2
    assert stream.frames_unmatched == 2

    stream._on_message({"tk": "11536", "ltp": "2500"})
    assert stream.frames_received == 3
    assert stream.frames_unmatched == 2
    assert stream.snapshot()["RELIANCE"].ltp == 2500.0


# ---- a dropped socket ------------------------------------------------
#
# Kotak drops the connection: idle timeouts, network blips, a session ending.
# Nothing reconnected, so the first drop was permanent — and because the mode
# stayed "live", the app reported a working feed with no prices behind it for
# the rest of the session.


def test_a_dropped_socket_is_resubscribed():
    import threading as th

    from livegraph.feed import Instrument, Segment, TickStream, stream as stream_module

    calls = []

    class Client:
        def subscribe(self, **kwargs):
            calls.append(kwargs)

        def un_subscribe(self, **kwargs):
            pass

    instruments = [Instrument("11536", Segment.FNO, "RELIANCE25SEPFUT", "RELIANCE")]
    stream = TickStream(Client(), instruments, loop=None)
    #: No waiting in a test; the backoff itself is not what is being checked.
    stream_module.RECONNECT_BACKOFF_SECONDS = (0,)

    stream.start()
    assert len(calls) == 1

    resubscribed = th.Event()
    original = stream._subscribe_all

    def watched():
        original()
        resubscribed.set()

    stream._subscribe_all = watched
    stream._on_close("Connection to remote host was lost.")

    assert resubscribed.wait(timeout=2), "a dropped socket was never resubscribed"
    assert stream.reconnects == 1


def test_closing_during_shutdown_does_not_reconnect():
    """`stop()` closes the socket itself; chasing that would be a loop."""
    from livegraph.feed import Instrument, Segment, TickStream

    class Client:
        def subscribe(self, **kwargs): pass
        def un_subscribe(self, **kwargs): pass

    stream = TickStream(Client(), [Instrument("1", Segment.FNO, "INFY25SEPFUT", "INFY")])
    stream.start()
    stream.stop()
    stream._on_close("The Session has been Closed!")

    assert stream.reconnects == 0
    assert not stream.is_connected


def test_a_session_that_kotak_closed_is_never_retried():
    """The storm this prevents was mine, and it is worth stating plainly.

    "The Session has been Closed!" is Kotak ending the session, not the socket
    dropping. Resubscribing cannot recover it, and every attempt produced
    another close, which produced another attempt. The container filled its log
    with one line until it was stopped by hand.
    """
    from livegraph.feed import Instrument, Segment, TickStream

    calls = []

    class Client:
        def subscribe(self, **kwargs):
            calls.append(kwargs)

        def un_subscribe(self, **kwargs):
            pass

    stream = TickStream(Client(), [Instrument("1", Segment.FNO, "INFY25SEPFUT", "INFY")])
    stream.start()
    assert len(calls) == 1

    for _ in range(20):
        stream._on_close("The Session has been Closed!")

    assert stream.session_ended
    assert len(calls) == 1, "a closed session must not be resubscribed"
    assert stream.reconnects == 0


def test_many_closes_for_one_drop_start_one_reconnect():
    """Kotak sends a close per subscribed batch, so a drop arrives many times.

    Without a guard each one started a thread, and each resubscribe produced
    more closes. One drop has to mean one reconnect.
    """
    import threading as th

    from livegraph.feed import Instrument, Segment, TickStream, stream as stream_module

    stream_module.RECONNECT_BACKOFF_SECONDS = (0.05,)
    started = []
    release = th.Event()

    class Client:
        def subscribe(self, **kwargs):
            started.append(kwargs)
            #: Hold the first reconnect open so the later closes race it.
            release.wait(timeout=1)

        def un_subscribe(self, **kwargs):
            pass

    stream = TickStream(Client(), [Instrument("1", Segment.FNO, "INFY25SEPFUT", "INFY")])
    stream.start()
    baseline = len(started)

    for _ in range(15):
        stream._on_close("Connection to remote host was lost.")
    release.set()

    #: One reconnect thread, so at most one further subscribe.
    th.Event().wait(0.4)
    assert len(started) - baseline <= 1, f"{len(started) - baseline} reconnects for one drop"
