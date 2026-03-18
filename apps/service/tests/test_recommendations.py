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


def test_recommendation_lifecycle_closes_and_persists_labels(tmp_path) -> None:
    store = SQLiteMarketDataStore(db_path=tmp_path / "runtime.sqlite3")
    _seed_store(store)
    service = RecommendationService(store=store)
    service.save_strategy_text("Lifecycle test strategy")
    service.generate_from_signals()
    items = service.list()
    assert items
    rec = items[0]

    if rec.direction == "long":
        close_price = rec.entry_price + 25000.0
    else:
        close_price = rec.entry_price - 25000.0

    store.save_market_bars(
        [
            MarketBar(
                symbol=rec.symbol,
                timeframe="1m",
                open=close_price,
                high=close_price,
                low=close_price,
                close=close_price,
                volume=2000,
                as_of="2026-03-14T09:59:00Z",
            )
        ]
    )
    closed = service.evaluate_lifecycle()
    assert closed >= 1
    detail = service.get(rec.recommendation_id)
    assert detail is not None
    assert detail.status == "closed"
    assert detail.close_reason in {"profit_trigger", "loss_trigger", "cutoff_trigger"}
    assert detail.close_price is not None
    assert detail.realized_pnl_per_lot is not None
    assert detail.closed_at is not None


def test_recommendation_lifecycle_uses_lot_size_for_pnl(tmp_path) -> None:
    store = SQLiteMarketDataStore(db_path=tmp_path / "runtime.sqlite3")
    _seed_store(store)
    service = RecommendationService(store=store)
    service.save_strategy_text("Lot size lifecycle strategy")
    service.generate_from_signals()
    rec = service.list()[0]

    store.save_instrument_specs(
        [
            {
                "symbol": rec.symbol,
                "lot_size": 50,
                "expiry_date": "2099-12-31",
                "source": "test",
            }
        ]
    )
    close_price = rec.entry_price + 500.0 if rec.direction == "long" else rec.entry_price - 500.0
    store.save_market_bars(
        [
            MarketBar(
                symbol=rec.symbol,
                timeframe="1m",
                open=close_price,
                high=close_price,
                low=close_price,
                close=close_price,
                volume=1000,
                as_of="2026-03-14T10:00:00Z",
            )
        ]
    )
    closed = service.evaluate_lifecycle()
    assert closed >= 1
    detail = service.get(rec.recommendation_id)
    assert detail is not None
    assert detail.close_reason == "profit_trigger"
    assert detail.realized_pnl_per_lot == 25000.0


def test_recommendation_lifecycle_uses_expiry_cutoff_when_available(tmp_path) -> None:
    store = SQLiteMarketDataStore(db_path=tmp_path / "runtime.sqlite3")
    _seed_store(store)
    service = RecommendationService(store=store)
    service.save_strategy_text("Expiry cutoff strategy")
    service.generate_from_signals()
    rec = service.list()[0]

    store.save_instrument_specs(
        [
            {
                "symbol": rec.symbol,
                "lot_size": 1,
                "expiry_date": "2000-01-01",
                "source": "test",
            }
        ]
    )
    store.save_market_bars(
        [
            MarketBar(
                symbol=rec.symbol,
                timeframe="1m",
                open=rec.entry_price,
                high=rec.entry_price,
                low=rec.entry_price,
                close=rec.entry_price,
                volume=1000,
                as_of="2026-03-14T10:01:00Z",
            )
        ]
    )
    closed = service.evaluate_lifecycle()
    assert closed >= 1
    detail = service.get(rec.recommendation_id)
    assert detail is not None
    assert detail.close_reason == "cutoff_trigger"


def test_recommendation_guardrail_rejects_low_risk_reward() -> None:
    verdict = RecommendationService._guardrail_check(
        confidence=0.7,
        entry_price=100.0,
        stop_loss=99.0,
        target_1=100.5,
        rationale="Valid rationale",
        risk_reward_ratio=0.5,
        spread_ratio=0.01,
        volatility_regime="medium",
    )
    assert verdict["ok"] is False
    assert verdict["reason"] == "risk_reward_below_threshold"


def test_recommendation_guardrail_uses_higher_confidence_threshold_for_high_volatility() -> None:
    verdict = RecommendationService._guardrail_check(
        confidence=0.3,
        entry_price=100.0,
        stop_loss=98.0,
        target_1=103.0,
        rationale="Valid rationale",
        risk_reward_ratio=1.5,
        spread_ratio=0.02,
        volatility_regime="high",
    )
    assert verdict["ok"] is False
    assert verdict["reason"] == "confidence_below_threshold"
