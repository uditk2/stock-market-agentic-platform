from __future__ import annotations

import csv
import json
import logging
import re
import socket
import urllib.parse
import urllib.error
import urllib.request
from datetime import datetime
from io import StringIO
from typing import Any

from smap_service.core.interfaces import MarketBar, MarketFeedClient
from smap_service.core.retry import retry_call
from smap_service.db.provider_credentials import SQLiteProviderCredentialStore

logger = logging.getLogger(__name__)


class _KotakAuthError(Exception):
    pass


class KotakMarketFeedClient(MarketFeedClient):
    _DEFAULT_BASE_URLS = (
        "https://mis.kotaksecurities.com",
        "https://e21.kotaksecurities.com",
        "https://e22.kotaksecurities.com",
        "https://e41.kotaksecurities.com",
        "https://e43.kotaksecurities.com",
        "https://gw-napi.kotaksecurities.com",
        "https://napi.kotaksecurities.com",
        "https://mnapi.kotaksecurities.com",
        "https://cnapi.kotaksecurities.com",
    )
    _SCRIP_MASTER_PATHS = (
        "/Files/1.0/masterscrip/v2/file-paths",
        "/script-details/1.0/masterscrip/file-paths",
    )
    _QUOTE_PATHS = (
        "/apim/quotes/1.0/quotes/neosymbol/{neo_symbol}/ohlc",
        "/apim/quotes/1.0/quotes/neosymbol/{neo_symbol}/all",
        "/script-details/1.0/quotes/neosymbol/{neo_symbol}/ohlc",
        "/script-details/1.0/quotes/neosymbol/{neo_symbol}/all",
    )

    def __init__(
        self,
        credentials: SQLiteProviderCredentialStore,
        base_url: str = "https://mis.kotaksecurities.com",
        timeout_seconds: float = 5.0,
    ):
        self._credentials = credentials
        self._base_urls = self._build_base_url_candidates(base_url)
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
        except _KotakAuthError:
            return {
                "ok": False,
                "code": "invalid_credentials",
                "message": "Kotak token was rejected by upstream authentication.",
            }
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                return {
                    "ok": False,
                    "code": "invalid_credentials",
                    "message": "Kotak token was rejected by upstream authentication.",
                }
            return {
                "ok": False,
                "code": "upstream_response_error",
                "message": f"Kotak upstream returned HTTP {exc.code}.",
            }
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
            payload = self._request_json(
                paths=tuple(path.format(neo_symbol=neo_symbol) for path in self._QUOTE_PATHS),
                token=token,
            )
            normalized_payload = self._extract_quote_payload(payload)
            return self._normalize(symbol=symbol, payload=normalized_payload)

        try:
            return retry_call(_request, attempts=3, base_delay_seconds=0.25)
        except _KotakAuthError as exc:
            logger.warning("kotak fetch failed symbol=%s error=invalid_credentials detail=%s", symbol, exc)
            return None
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
        payload = self._request_json(paths=self._SCRIP_MASTER_PATHS, token=token)
        if not isinstance(payload, dict):
            return {}
        data = payload.get("data")
        for candidate in (data, payload):
            if not isinstance(candidate, dict):
                continue
            for key in ("filesPaths", "filePaths", "paths", "files"):
                values = candidate.get(key)
                if isinstance(values, list):
                    parsed = [str(item).strip() for item in values if isinstance(item, str) and str(item).strip()]
                    if parsed:
                        return parsed
        return []

    def _request_json(self, paths: tuple[str, ...], token: str) -> Any:
        errors: list[Exception] = []
        auth_errors: list[Exception] = []
        for base_url in self._base_urls:
            for path in paths:
                full_url = f"{base_url}/{path.lstrip('/')}"
                for auth_value in self._auth_values(token):
                    request = urllib.request.Request(
                        full_url,
                        headers={
                            "Authorization": auth_value,
                            "Content-Type": "application/x-www-form-urlencoded",
                            "User-Agent": "smap-service/0.1",
                        },
                        method="GET",
                    )
                    try:
                        with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                            return json.loads(response.read().decode("utf-8"))
                    except urllib.error.HTTPError as exc:
                        if exc.code in (401, 403):
                            auth_errors.append(exc)
                            continue
                        if exc.code == 404:
                            continue
                        errors.append(exc)
                    except urllib.error.URLError as exc:
                        errors.append(exc)
        if auth_errors:
            last = auth_errors[-1]
            raise _KotakAuthError(f"auth_failed status={getattr(last, 'code', 'unknown')}") from last
        if errors:
            raise errors[-1]
        raise urllib.error.URLError("No Kotak endpoint candidates available.")

    @staticmethod
    def _build_base_url_candidates(base_url: str) -> tuple[str, ...]:
        ordered = [base_url, *KotakMarketFeedClient._DEFAULT_BASE_URLS]
        seen: set[str] = set()
        output: list[str] = []
        for item in ordered:
            value = str(item or "").strip().rstrip("/")
            if not value or value in seen:
                continue
            seen.add(value)
            output.append(value)
        return tuple(output)

    @staticmethod
    def _auth_values(token: str) -> tuple[str, ...]:
        raw = str(token or "").strip()
        if not raw:
            return tuple()
        if raw.lower().startswith("bearer "):
            return (raw,)
        return (raw, f"Bearer {raw}")

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
    def _extract_quote_payload(payload: Any) -> dict[str, Any]:
        if isinstance(payload, list) and payload:
            first = payload[0]
            if isinstance(first, dict):
                nested_ohlc = first.get("ohlc")
                if isinstance(nested_ohlc, dict):
                    return nested_ohlc
                return first
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
