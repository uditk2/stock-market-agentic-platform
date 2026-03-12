from smap_service.core.retry import retry_call
from smap_service.ingestion.jobs import ingest_market_bars
from smap_service.plugins.market.kotak_client import KotakMarketFeedClient
from smap_service.db.provider_credentials import SQLiteProviderCredentialStore


class _DummyMarketClient:
    @property
    def name(self) -> str:
        return "dummy"

    def fetch_latest_bars(self, symbols: list[str]):
        return [{"symbol": symbol} for symbol in symbols]


def test_retry_call_retries_then_succeeds() -> None:
    state = {"count": 0}

    def _call() -> int:
        state["count"] += 1
        if state["count"] < 3:
            raise RuntimeError("temporary")
        return 7

    assert retry_call(_call, attempts=3, base_delay_seconds=0.0) == 7
    assert state["count"] == 3


def test_kotak_client_without_selected_credentials_returns_empty(tmp_path) -> None:
    store = SQLiteProviderCredentialStore(
        db_path=tmp_path / "runtime.sqlite3",
        key_path=tmp_path / "credentials.key",
    )
    client = KotakMarketFeedClient(credentials=store)
    assert client.fetch_latest_bars(["NIFTY-FUT"]) == []


def test_ingest_market_bars_counts_records() -> None:
    result = ingest_market_bars(_DummyMarketClient())
    assert result.records_processed == 4
