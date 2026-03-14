from smap_service.core.interfaces import MarketBar, NewsItem
from smap_service.core.recommendations import RecommendationService
from smap_service.core.signals import compute_signals_from_store
from smap_service.db.market_data import SQLiteMarketDataStore


def _seed_store(store: SQLiteMarketDataStore) -> None:
    bars = [
        MarketBar(
            symbol="TCS-FUT",
            timeframe="1m",
            open=100 + idx,
            high=101 + idx,
            low=99 + idx,
            close=100.7 + idx,
            volume=1000 + (idx * 100),
            as_of=f"2026-03-14T08:{idx:02d}:00Z",
        )
        for idx in range(10)
    ]
    store.save_market_bars(bars)
    store.save_news_items(
        [
            NewsItem(
                source="nse_announcements",
                external_id="evt-tcs",
                headline="TCS strong growth outlook",
                body="Strong growth and momentum",
                symbols=["TCS-FUT"],
                published_at="2026-03-14T08:20:00Z",
            )
        ],
        channel="nse_announcements",
    )
    signals = compute_signals_from_store(store)
    store.save_signals(signals)


def test_recommendations_default_sort_is_confidence_desc(tmp_path) -> None:
    store = SQLiteMarketDataStore(db_path=tmp_path / "runtime.sqlite3")
    _seed_store(store)
    service = RecommendationService(store=store)
    service.save_strategy_text("Trend + momentum strategy")
    service.generate_from_signals()

    items = service.list()
    assert items
    confidences = [item.confidence for item in items]
    assert confidences == sorted(confidences, reverse=True)


def test_recommendations_search_filters_symbol(tmp_path) -> None:
    store = SQLiteMarketDataStore(db_path=tmp_path / "runtime.sqlite3")
    _seed_store(store)
    service = RecommendationService(store=store)
    service.save_strategy_text("Trend + momentum strategy")
    service.generate_from_signals()

    items = service.list(query="tcs")
    assert len(items) >= 1
    assert items[0].symbol == "TCS-FUT"
