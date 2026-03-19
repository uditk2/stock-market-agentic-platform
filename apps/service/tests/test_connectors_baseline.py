import socket
import urllib.error
from io import BytesIO

from smap_service.core.retry import retry_call
from smap_service.ingestion.jobs import ingest_market_bars
from smap_service.plugins.market.kotak_client import (
    KotakMarketFeedClient,
    _extract_expiry_date,
    _extract_lot_size,
    _extract_symbol_root,
)
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
    assert result.records_processed >= 20
    assert result.attribution is not None
    assert result.attribution["symbols_dynamic_count"] == 0
    assert result.attribution["symbols_merged_count"] == result.records_processed


def test_kotak_verify_credentials_reports_upstream_timeout(tmp_path, monkeypatch) -> None:
    store = SQLiteProviderCredentialStore(
        db_path=tmp_path / "runtime.sqlite3",
        key_path=tmp_path / "credentials.key",
    )
    store.save_selection(provider="kotak_neo", credentials={"access_token": "token"})
    client = KotakMarketFeedClient(credentials=store)

    def _timeout(token: str) -> list[str]:
        raise urllib.error.URLError(socket.timeout("timed out"))

    monkeypatch.setattr(client, "_fetch_scrip_master_paths", _timeout)
    result = client.verify_credentials()
    assert result["ok"] is False
    assert result["code"] == "upstream_timeout"


def test_kotak_verify_credentials_reports_invalid_credentials(tmp_path, monkeypatch) -> None:
    store = SQLiteProviderCredentialStore(
        db_path=tmp_path / "runtime.sqlite3",
        key_path=tmp_path / "credentials.key",
    )
    store.save_selection(provider="kotak_neo", credentials={"access_token": "token"})
    client = KotakMarketFeedClient(credentials=store)

    def _invalid(token: str) -> list[str]:
        raise urllib.error.HTTPError(
            url="https://gw-napi.kotaksecurities.com/Files/1.0/masterscrip/v2/file-paths",
            code=401,
            msg="unauthorized",
            hdrs=None,
            fp=BytesIO(),
        )

    monkeypatch.setattr(client, "_fetch_scrip_master_paths", _invalid)
    result = client.verify_credentials()
    assert result["ok"] is False
    assert result["code"] == "invalid_credentials"


def test_kotak_request_json_fallbacks_on_404(monkeypatch, tmp_path) -> None:
    store = SQLiteProviderCredentialStore(
        db_path=tmp_path / "runtime.sqlite3",
        key_path=tmp_path / "credentials.key",
    )
    client = KotakMarketFeedClient(credentials=store, base_url="https://first.example.com")
    client._base_urls = ("https://first.example.com", "https://second.example.com")
    calls: list[str] = []

    class _Response:
        def __init__(self, payload: str):
            self._payload = payload

        def read(self) -> bytes:
            return self._payload.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def _urlopen(request, timeout=0):  # noqa: ANN001
        calls.append(request.full_url)
        if request.full_url.endswith("/first"):
            raise urllib.error.HTTPError(request.full_url, 404, "not found", hdrs=None, fp=BytesIO())
        return _Response('{"data":{"filesPaths":["https://example.com/master.csv"]}}')

    monkeypatch.setattr("urllib.request.urlopen", _urlopen)
    payload = client._request_json(paths=("/first", "/second"), token="Bearer abc")
    assert payload["data"]["filesPaths"][0] == "https://example.com/master.csv"
    assert calls == [
        "https://first.example.com/first",
        "https://first.example.com/second",
    ]


def test_extract_symbol_root_parses_stock_future_symbols() -> None:
    assert _extract_symbol_root("RELIANCE24MARFUT") == "RELIANCE"
    assert _extract_symbol_root("NIFTY24MARFUT") == "NIFTY"


def test_kotak_extracts_lot_size_and_expiry_from_master_rows() -> None:
    row = {
        "pTrdSymbol": "RELIANCE27MAR2026FUT",
        "lotSize": "250",
        "expiryDate": "27-03-2026",
    }
    assert _extract_lot_size(row) == 250.0
    assert _extract_expiry_date(row) == "2026-03-27"


def test_kotak_extract_quote_payload_handles_list_ohlc_shape(tmp_path) -> None:
    store = SQLiteProviderCredentialStore(
        db_path=tmp_path / "runtime.sqlite3",
        key_path=tmp_path / "credentials.key",
    )
    client = KotakMarketFeedClient(credentials=store)
    payload = [
        {
            "exchange_token": "70537",
            "display_symbol": "MIDCPNIFTY26MAY12625PE",
            "ohlc": {"open": "1", "high": "2", "low": "0.5", "close": "1.5"},
        }
    ]
    normalized = client._extract_quote_payload(payload)
    assert normalized["open"] == "1"
    assert normalized["close"] == "1.5"
