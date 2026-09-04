"""Regressions guarded here:

- The feed mode must always reach the client. A simulated price rendered as a
  live one is the single most dangerous defect in this app.
- /api/graph must drop IN_SECTOR edges when sector hubs are excluded, otherwise
  the payload carries edges pointing at nodes it did not send and the UI
  renders dangling links.
- The websocket must coalesce to one frame per symbol per flush, not one frame
  per tick, or a 200-symbol universe floods the browser.
"""

import time

import pytest
from fastapi.testclient import TestClient

from livegraph.api import create_app


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(simulate=True)) as c:
        #: The simulator needs a couple of intervals before anything is priced.
        time.sleep(6)
        yield c


def test_health_reports_graph_and_feed(client):
    body = client.get("/api/health").json()
    assert body["ok"] is True
    assert body["graph"] == {"nodes": 545, "edges": 3003}
    assert body["feed"]["mode"] == "simulated"


def test_feed_mode_is_always_disclosed(client):
    """A simulated price must never be presentable as live."""
    status = client.get("/api/market/status").json()
    assert status["mode"] == "simulated"
    assert status["connected"] is True
    assert status["symbols_priced"] > 0


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


def test_websocket_sends_a_snapshot_then_coalesced_batches(client):
    with client.websocket_connect("/ws/ticks") as ws:
        first = ws.receive_json()
        assert first["type"] == "snapshot"
        assert len(first["ticks"]) > 0

        batch = ws.receive_json()
        assert batch["type"] == "ticks"
        symbols = [t["symbol"] for t in batch["ticks"]]
        #: One entry per symbol per flush, never one frame per tick.
        assert len(symbols) == len(set(symbols))


def test_simulated_moves_do_not_park_on_the_clamp():
    """Regression: a pure random walk drifted to +/-9% and stayed there.

    Once every symbol pins to the clamp, the divergence scan has no spread left
    to measure and the whole app looks broken in demo mode.
    """
    from livegraph.feed.simulator import SimulatedFeed

    symbols = [f"S{i}" for i in range(40)]
    feed = SimulatedFeed(
        symbols=symbols,
        sectors={s: "Sector" for s in symbols},
        peer_groups={s: "Group" for s in symbols},
        interval_seconds=0.01,
    )
    for _ in range(4000):
        feed._step()

    changes = [abs(tick.change_pct) for tick in feed.snapshot().values()] or [
        abs(v) for v in feed._change.values()
    ]
    pinned = sum(1 for c in changes if c >= 8.9)
    assert pinned == 0, f"{pinned}/{len(changes)} symbols parked on the clamp"


def test_simulated_feed_produces_idiosyncratic_moves():
    """Regression: a purely sector-driven simulator made the scan useless.

    With every move driven by sector and peer factors, the peer gap was always
    tiny and the verdict was always "sector-wide", so a correct classifier
    looked broken. Some names must break away from their own peer group.
    """
    import statistics

    from livegraph.feed.simulator import SimulatedFeed

    symbols = [f"S{i}" for i in range(60)]
    feed = SimulatedFeed(
        symbols=symbols,
        sectors={s: "Sector" for s in symbols},
        peer_groups={s: "Group" for s in symbols},
        interval_seconds=0.01,
    )
    for _ in range(600):
        feed._step()

    moves = [t.change_pct for t in feed.snapshot().values()]
    mean = statistics.fmean(moves)
    gaps = [abs(m - mean) for m in moves]
    assert max(gaps) > 0.75, f"no name broke away from the group; widest gap {max(gaps):.2f}pp"
