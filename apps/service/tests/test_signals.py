from smap_service.core.interfaces import MarketBar, NewsItem
from smap_service.core.signals import compute_signals_from_store
from smap_service.db.market_data import SQLiteMarketDataStore


def test_signal_engine_produces_stable_ids_and_persists(tmp_path) -> None:
    store = SQLiteMarketDataStore(db_path=tmp_path / "runtime.sqlite3")
    bars = [
        MarketBar(
            symbol="RELIANCE-FUT",
            timeframe="1m",
            open=100 + idx,
            high=101 + idx,
            low=99 + idx,
            close=100.5 + idx,
            volume=1000 + (idx * 100),
            as_of=f"2026-03-14T07:{idx:02d}:00Z",
        )
        for idx in range(8)
    ]
    store.save_market_bars(bars)
    store.save_news_items(
        [
            NewsItem(
                source="nse_announcements",
                external_id="evt-1",
                headline="Reliance strong growth update",
                body="Company reports strong growth and demand surge",
                symbols=["RELIANCE-FUT"],
                published_at="2026-03-14T07:10:00Z",
            )
        ],
        channel="nse_announcements",
    )
    first = compute_signals_from_store(store)
    second = compute_signals_from_store(store)
    assert first
    assert second
    assert first[0].signal_id == second[0].signal_id
    assert store.save_signals(first) == len(first)
