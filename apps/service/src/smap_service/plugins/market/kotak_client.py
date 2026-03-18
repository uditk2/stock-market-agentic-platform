from __future__ import annotations

import csv
import json
import logging
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from io import StringIO
from typing import Any

from smap_service.core.interfaces import MarketBar, MarketFeedClient
from smap_service.core.retry import retry_call
from smap_service.db.provider_credentials import SQLiteProviderCredentialStore

logger = logging.getLogger(__name__)


class KotakMarketFeedClient(MarketFeedClient):
    def __init__(
        self,
        credentials: SQLiteProviderCredentialStore,
        base_url: str = "https://mnapi.kotaksecurities.com",
        timeout_seconds: float = 5.0,
    ):
        self._credentials = credentials
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._token_cache: dict[str, str] | None = None

    @property
    def name(self) -> str:
        return "kotak_neo"

    def fetch_latest_bars(self, symbols: list[str]) -> list[MarketBar]:
        selection = self._credentials.get_selection()
        if selection.provider != "kotak_neo" or not selection.has_credentials:
            logger.info("kotak connector skipped: selected_provider=%s", selection.provider)
            return []
        creds = self._credentials.get_credentials("kotak_neo") or {}
        token = creds.get("access_token")
        if not token:
            logger.warning("kotak connector skipped: missing access_token")
            return []
        if not self.verify_credentials().get("ok"):
            logger.warning("kotak connector skipped: credential verification failed")
            return []
        symbol_tokens = self._resolve_symbol_tokens(symbols=symbols, token=token)
        bars: list[MarketBar] = []
        for symbol in symbols:
            instrument_token = symbol_tokens.get(symbol)
            if not instrument_token:
                logger.warning("kotak fetch skipped symbol=%s reason=token_not_found", symbol)
                continue
            item = self._fetch_symbol(symbol=symbol, instrument_token=instrument_token, token=token)
            if item is not None:
                bars.append(item)
        return bars

    def list_active_stock_futures_symbols(self, limit: int = 400) -> list[str]:
        selection = self._credentials.get_selection()
        if selection.provider != "kotak_neo" or not selection.has_credentials:
            return []
        creds = self._credentials.get_credentials("kotak_neo") or {}
        token = creds.get("access_token")
        if not token:
            return []
        paths = self._fetch_scrip_master_paths(token=token)
        futures_csv_url = next((path for path in paths if "nse_fo" in path.lower()), "")
        if not futures_csv_url:
            return []
        rows = self._fetch_csv_rows(futures_csv_url)
        excluded_index_roots = {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX", "BANKEX"}
        discovered: list[str] = []
        seen: set[str] = set()
        for row in rows:
            raw = self._pick_first(row, ("pTrdSymbol", "trading_symbol", "symbol", "pSymbolName"))
            if not raw:
                continue
            root = _extract_symbol_root(raw.upper())
            if not root or root in excluded_index_roots:
                continue
            symbol = f"{root}-FUT"
            if symbol in seen:
                continue
            seen.add(symbol)
            discovered.append(symbol)
            if len(discovered) >= limit:
                break
        return sorted(discovered)

    def fetch_instrument_specs(self, symbols: list[str]) -> dict[str, dict[str, object]]:
        selection = self._credentials.get_selection()
        if selection.provider != "kotak_neo" or not selection.has_credentials:
            return {}
        creds = self._credentials.get_credentials("kotak_neo") or {}
        token = creds.get("access_token")
        if not token:
            return {}
        paths = self._fetch_scrip_master_paths(token=token)
        futures_csv_url = next((path for path in paths if "nse_fo" in path.lower()), "")
        if not futures_csv_url:
            return {}
        rows = self._fetch_csv_rows(futures_csv_url)
        output: dict[str, dict[str, object]] = {}
        for symbol in symbols:
            row = self._find_row_for_symbol(symbol=symbol, rows=rows)
            if row is None:
                continue
            lot_size = _extract_lot_size(row)
            expiry_date = _extract_expiry_date(row)
            if lot_size is None and expiry_date is None:
                continue
            output[symbol] = {
                "lot_size": lot_size,
                "expiry_date": expiry_date,
                "source": "kotak_master",
            }
        return output

    def verify_credentials(self) -> dict[str, Any]:
        selection = self._credentials.get_selection()
        if selection.provider != "kotak_neo" or not selection.has_credentials:
            return {
                "ok": False,
                "code": "provider_not_selected",
                "message": "Kotak Neo is not selected or credentials are not saved.",
            }
        creds = self._credentials.get_credentials("kotak_neo") or {}
        return self.verify_credentials_payload(creds)

    def verify_credentials_payload(self, credentials: dict[str, str] | None) -> dict[str, Any]:
        creds = credentials or {}
        token = creds.get("access_token")
        if not token:
            return {"ok": False, "code": "missing_access_token", "message": "Missing access_token in provided credentials."}
        try:
            paths = self._fetch_scrip_master_paths(token=token)
            if not paths:
                return {"ok": False, "code": "empty_scrip_master", "message": "Scrip master path list is empty."}
            return {"ok": True, "code": "verified", "message": "Kotak credentials verified via scrip-master endpoint."}
        except urllib.error.URLError as exc:  # pragma: no cover - runtime/network wrapper
            reason = getattr(exc, "reason", None)
            if isinstance(reason, socket.timeout):
                return {
                    "ok": False,
                    "code": "upstream_timeout",
                    "message": "Timed out while contacting Kotak verification endpoint.",
                }
            return {"ok": False, "code": "upstream_unreachable", "message": str(exc)}
        except Exception as exc:  # pragma: no cover - runtime/network wrapper
            return {"ok": False, "code": "verify_failed", "message": str(exc)}

    def _fetch_symbol(self, symbol: str, instrument_token: str, token: str) -> MarketBar | None:
        def _request() -> MarketBar | None:
            neo_symbol = urllib.parse.quote(f"nse_fo|{instrument_token}", safe="")
            request = urllib.request.Request(
                f"{self._base_url}/script-details/1.0/quotes/neosymbol/{neo_symbol}/ohlc",
                headers={
                    "Authorization": token,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "smap-service/0.1",
                },
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            normalized_payload = self._extract_quote_payload(payload)
            return self._normalize(symbol=symbol, payload=normalized_payload)

        try:
            return retry_call(_request, attempts=3, base_delay_seconds=0.25)
        except Exception as exc:  # pragma: no cover - network/runtime wrapper
            logger.warning("kotak fetch failed symbol=%s error=%s", symbol, exc)
            return None

    def _resolve_symbol_tokens(self, symbols: list[str], token: str) -> dict[str, str]:
        if self._token_cache is not None:
            return {symbol: self._token_cache.get(symbol, "") for symbol in symbols}
        paths = self._fetch_scrip_master_paths(token=token)
        futures_csv_url = next((path for path in paths if "nse_fo" in path.lower()), "")
        if not futures_csv_url:
            logger.warning("kotak token resolution failed: nse_fo scrip master path missing")
            self._token_cache = {}
            return {}
        rows = self._fetch_csv_rows(futures_csv_url)
        resolved: dict[str, str] = {}
        for symbol in symbols:
            token_value = self._find_token_for_symbol(symbol=symbol, rows=rows)
            if token_value:
                resolved[symbol] = token_value
        self._token_cache = resolved
        return resolved

    def _fetch_scrip_master_paths(self, token: str) -> list[str]:
        request = urllib.request.Request(
            f"{self._base_url}/script-details/1.0/masterscrip/file-paths",
            headers={
                "Authorization": token,
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "smap-service/0.1",
            },
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        data = payload.get("data", {})
        paths = data.get("filesPaths", [])
        if isinstance(paths, list):
            return [str(item) for item in paths if isinstance(item, str)]
        return []

    def _fetch_csv_rows(self, url: str) -> list[dict[str, str]]:
        with urllib.request.urlopen(url, timeout=self._timeout_seconds) as response:
            csv_text = response.read().decode("utf-8", errors="replace")
        reader = csv.DictReader(StringIO(csv_text))
        return [{str(k): str(v) for k, v in row.items()} for row in reader]

    @staticmethod
    def _find_token_for_symbol(symbol: str, rows: list[dict[str, str]]) -> str | None:
        row = KotakMarketFeedClient._find_row_for_symbol(symbol=symbol, rows=rows)
        if row is None:
            return None
        token_keys = ("pSymbol", "instrument_token", "token", "pToken")
        for key in token_keys:
            value = row.get(key)
            if value and str(value).strip():
                return str(value).strip()
        return None

    @staticmethod
    def _find_row_for_symbol(symbol: str, rows: list[dict[str, str]]) -> dict[str, str] | None:
        base = symbol.replace("-FUT", "").upper()
        label_keys = ("pTrdSymbol", "trading_symbol", "symbol", "pSymbolName")
        for row in rows:
            label = ""
            for key in label_keys:
                value = row.get(key)
                if value:
                    label = str(value).upper()
                    break
            if not label or base not in label:
                continue
            if "FUT" not in label:
                continue
            return row
        return None

    @staticmethod
    def _pick_first(row: dict[str, str], keys: tuple[str, ...]) -> str:
        for key in keys:
            value = row.get(key)
            if value and str(value).strip():
                return str(value).strip()
        return ""

    @staticmethod
    def _extract_quote_payload(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data")
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                return first
        if isinstance(data, dict):
            return data
        return payload

    @staticmethod
    def _normalize(symbol: str, payload: dict[str, object]) -> MarketBar:
        # Kotak payload keys can vary across quote types/account tiers.
        open_value = payload.get("open", payload.get("op", 0.0))
        high_value = payload.get("high", payload.get("h", 0.0))
        low_value = payload.get("low", payload.get("lo", 0.0))
        close_value = payload.get("close", payload.get("c", payload.get("ltp", 0.0)))
        volume_value = payload.get("volume", payload.get("v", 0))
        as_of_value = payload.get("as_of", payload.get("ltt", payload.get("timestamp", "")))
        return MarketBar(
            symbol=symbol,
            timeframe="1m",
            open=float(open_value or 0.0),
            high=float(high_value or 0.0),
            low=float(low_value or 0.0),
            close=float(close_value or 0.0),
            volume=int(volume_value or 0),
            as_of=str(as_of_value or ""),
        )


def _extract_symbol_root(label: str) -> str:
    match = re.match(r"([A-Z&]+?)(\d{2}[A-Z]{3}FUT)", label)
    if match:
        return match.group(1)
    return ""


def _extract_lot_size(row: dict[str, str]) -> float | None:
    candidate_keys = ("lot_size", "lotsize", "lotSize", "pLotSize", "dLotSize", "qty", "quantity")
    for key in candidate_keys:
        value = row.get(key)
        if not value:
            continue
        text = str(value).strip().replace(",", "")
        try:
            parsed = float(text)
        except ValueError:
            continue
        if parsed > 0:
            return parsed
    return None


def _extract_expiry_date(row: dict[str, str]) -> str | None:
    candidate_keys = ("expiry_date", "expiry", "expiryDate", "pExpiryDate", "expDate")
    for key in candidate_keys:
        value = row.get(key)
        parsed = _parse_date_text(str(value).strip()) if value else None
        if parsed:
            return parsed
    return None


def _parse_date_text(raw: str) -> str | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%b-%Y", "%d%b%Y", "%d%b%y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None
