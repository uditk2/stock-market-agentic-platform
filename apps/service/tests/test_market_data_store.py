from smap_service.core.interfaces import MarketBar, NewsItem
from smap_service.db.market_data import SQLiteMarketDataStore


def test_market_data_store_persists_market_bars_and_news(tmp_path) -> None:
    store = SQLiteMarketDataStore(db_path=tmp_path / "runtime.sqlite3")
    bars = [
        MarketBar(
            symbol="RELIANCE-FUT",
            timeframe="1m",
            open=100.0,
            high=101.0,
            low=99.5,
            close=100.5,
            volume=1234,
            as_of="2026-03-14T07:00:00Z",
        )
    ]
    items = [
        NewsItem(
            source="nse_announcements",
            external_id="evt-1",
            headline="Reliance update",
            body="Quarterly update",
            symbols=["RELIANCE-FUT"],
            published_at="2026-03-14T07:00:00Z",
        )
    ]
    assert store.save_market_bars(bars) == 1
    assert store.save_news_items(items, channel="nse_announcements") == 1
