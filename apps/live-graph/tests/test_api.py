"""Regressions guarded here:

- The feed mode must always reach the client, so a screen with no prices is
  never mistaken for a quiet market.
- /api/graph must drop IN_SECTOR edges when sector hubs are excluded, otherwise
  the payload carries edges pointing at nodes it did not send and the UI
  renders dangling links.
- The websocket must coalesce to one frame per symbol per flush, not one frame
  per tick, or a 200-symbol universe floods the browser.
"""

import pytest
from fastapi.testclient import TestClient

from fake_feed import FakeFeed

from livegraph.api import create_app


#: A small, deterministic universe spanning three sectors.
MOVES = [
    ("HDFCBANK", 1650.0, 1.31), ("ICICIBANK", 1180.0, 1.24), ("AXISBANK", 1090.0, 1.18),
    ("KOTAKBANK", 1750.0, 1.10), ("SBIN", 820.0, 0.95),
    ("TATAPOWER", 914.84, -1.77), ("NTPC", 388.15, -1.21), ("POWERGRID", 292.40, -1.18),
    ("INFY", 1500.0, -1.00), ("TCS", 3200.0, -1.20), ("WIPRO", 242.0, -0.90),
    ("RELIANCE", 1400.0, 2.00),
]


@pytest.fixture(scope="module")
def feed():
    return FakeFeed(MOVES)


@pytest.fixture(scope="module")
def client(feed):
    with TestClient(create_app(feed=feed)) as c:
        yield c


def test_health_reports_graph_and_feed(client):
    body = client.get("/api/health").json()
    assert body["ok"] is True
    assert body["graph"] == {"nodes": 545, "edges": 3003}
    assert body["feed"]["mode"] == "injected"


def test_feed_mode_is_always_disclosed(client):
    """The client must always be able to tell where prices came from."""
    status = client.get("/api/market/status").json()
    assert status["mode"] == "injected"
    assert status["connected"] is True
    assert status["symbols_priced"] == len(MOVES)


def test_without_credentials_there_is_no_feed_and_the_reason_is_given():
    """Regression: the app used to fall back to synthetic prices.

    Invented prices on a screen built to be acted on are worse than no prices,
    so an unconfigured app must show none and say why.
    """
    with TestClient(create_app()) as bare:
        status = bare.get("/api/market/status").json()
        assert status["mode"] == "unconfigured"
        assert status["symbols_priced"] == 0
        assert "credentials incomplete" in status["detail"]
        assert bare.get("/api/market/quotes").json() == []


def test_quotes_are_priced_and_typed(client):
    rows = client.get("/api/market/quotes").json()
    assert rows and all(r["ltp"] > 0 for r in rows)
    assert all(r["segment"] == "nse_fo" for r in rows)


def test_movers_respect_direction(client):
    up = client.get("/api/market/movers?limit=5&direction=up").json()
    down = client.get("/api/market/movers?limit=5&direction=down").json()
    assert [r["change_pct"] for r in up] == sorted((r["change_pct"] for r in up), reverse=True)
    assert [r["change_pct"] for r in down] == sorted(r["change_pct"] for r in down)


def test_graph_without_sector_hubs_has_no_dangling_edges(client):
    body = client.get("/api/graph?fo_only=true&include_sectors=false").json()
    ids = {n["id"] for n in body["nodes"]}
    assert not any(n["id"].startswith("SEC::") for n in body["nodes"])
    assert all(e["source"] in ids and e["target"] in ids for e in body["edges"])
    assert not any(e["type"] == "IN_SECTOR" for e in body["edges"])


def test_neighbourhood_is_centred_and_connected(client):
    body = client.get("/api/graph/node/RELIANCE?depth=1").json()
    ids = {n["id"] for n in body["nodes"]}
    assert "RELIANCE" in ids
    assert all(e["source"] in ids and e["target"] in ids for e in body["edges"])


def test_unknown_symbol_is_404(client):
    assert client.get("/api/graph/node/NOTASTOCK").status_code == 404
    assert client.get("/api/graph/impact/NOTASTOCK").status_code == 404


def test_impact_flips_with_direction(client):
    up = client.get("/api/graph/impact/CRUDE?direction=up&limit=10").json()
    down = client.get("/api/graph/impact/CRUDE?direction=down&limit=10").json()
    up_by_symbol = {r["symbol"]: r["relative_magnitude"] for r in up}
    for row in down:
        if row["symbol"] in up_by_symbol:
            assert row["relative_magnitude"] == pytest.approx(-up_by_symbol[row["symbol"]])


def test_sector_rollup_counts_add_up(client):
    for row in client.get("/api/graph/sectors").json():
        assert row["advancing"] + row["declining"] <= row["priced"]
        assert row["priced"] <= row["members"]




def test_scratchpad_health_reports_the_sandbox(client):
    body = client.get("/api/scratchpad/health").json()
    assert "sandbox_available" in body


def test_websocket_sends_a_snapshot_then_coalesced_batches(client, feed):
    with client.websocket_connect("/ws/ticks") as ws:
        first = ws.receive_json()
        assert first["type"] == "snapshot"
        assert len(first["ticks"]) == len(MOVES)

        #: Several updates for one symbol inside a single flush window must
        #: arrive as one entry, not three frames.
        for price in (1651.0, 1652.0, 1653.0):
            feed.emit("HDFCBANK", price, 1.35)

        batch = ws.receive_json()
        assert batch["type"] == "ticks"
        symbols = [t["symbol"] for t in batch["ticks"]]
        assert len(symbols) == len(set(symbols))
        assert "HDFCBANK" in symbols
        assert next(t for t in batch["ticks"] if t["symbol"] == "HDFCBANK")["ltp"] == 1653.0






def test_a_successful_login_starts_the_feed_when_none_is_running():
    """The Admin tab could log in and still show no prices without this.

    Replacing a *live* socket in place is a separate concern; starting one when
    the app came up unconfigured is safe, because there is nothing to tear down.
    """
    from unittest import mock

    from fake_feed import FakeFeed

    from livegraph.api.state import AppState
    from livegraph.feed import NoFeed

    state = AppState(feed=NoFeed("no credentials"))
    assert state.feed_mode != "live"

    replacement = FakeFeed([("INFY", 1500.0, -1.0)])
    session = mock.Mock()
    session.client = object()
    state.kotak_session = session

    with mock.patch.object(
        AppState, "_live_feed_from", return_value=(replacement, "live", "42 contracts")
    ):
        ok, message = state._start_live_feed(session.client)

    assert ok and "live" in message
    assert state.feed is replacement
    assert state.feed_mode == "live"
    #: The new feed must be wired to the tick handler, or prices arrive nowhere:
    #: a tick from it has to reach the state the API reads.
    replacement.emit("INFY", 1500.0, -1.0)
    assert "INFY" in state.ticks()


def test_an_injected_feed_is_not_replaced_by_a_login():
    from fake_feed import FakeFeed

    from livegraph.api.state import AppState

    state = AppState(feed=FakeFeed([("INFY", 1500.0, -1.0)]))
    existing = state.feed
    ok, message = state._start_live_feed(object())

    assert ok and "left alone" in message
    assert state.feed is existing


def test_a_feed_that_fails_to_start_does_not_lose_the_session():
    """The login worked; only the feed did not. Say both."""
    from unittest import mock

    from livegraph.api.state import AppState
    from livegraph.feed import NoFeed

    state = AppState(feed=NoFeed("no credentials"))
    with mock.patch.object(AppState, "_live_feed_from", side_effect=RuntimeError("boom")):
        ok, message = state._start_live_feed(object())

    assert ok is True
    assert "did not start" in message and "boom" in message
    assert state.feed_mode != "live"


def test_the_feed_starts_when_the_login_runs_off_the_event_loop():
    """An admin request runs in a worker thread, which has no event loop.

    `asyncio.get_event_loop()` raises there, and it was the first statement in
    TickStream.start() — so the subscribe never ran, the login returned 500,
    and the app reported a live feed that could not receive a tick.
    """
    import asyncio
    import threading
    from unittest import mock

    from fake_feed import FakeFeed

    from livegraph.api.state import AppState
    from livegraph.feed import NoFeed

    state = AppState(feed=NoFeed("no credentials"))

    async def capture_loop():
        state.start()

    asyncio.run(capture_loop())
    assert state._loop is not None

    replacement = FakeFeed([("INFY", 1500.0, -1.0)])
    outcome = {}

    def login_off_the_loop():
        with mock.patch.object(
            AppState, "_live_feed_from", return_value=(replacement, "live", "42 contracts")
        ):
            outcome["result"] = state._start_live_feed(object())

    worker = threading.Thread(target=login_off_the_loop)
    worker.start()
    worker.join()

    ok, message = outcome["result"]
    assert ok and "live" in message
    assert replacement.started, "the feed was registered but never subscribed"


def test_a_feed_that_cannot_start_does_not_leave_the_app_claiming_to_be_live():
    from unittest import mock

    from fake_feed import FakeFeed

    from livegraph.api.state import AppState
    from livegraph.feed import NoFeed

    original = NoFeed("no credentials")
    state = AppState(feed=original)

    exploding = FakeFeed([("INFY", 1500.0, -1.0)])
    with mock.patch.object(exploding, "start", side_effect=RuntimeError("no loop")):
        with mock.patch.object(
            AppState, "_live_feed_from", return_value=(exploding, "live", "42 contracts")
        ):
            ok, message = state._start_live_feed(object())

    assert ok is True and "did not start" in message
    #: The important part: not still saying "live" with nothing behind it.
    assert state.feed_mode != "live"
    assert state.feed is original
