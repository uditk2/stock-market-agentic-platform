from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request

from smap_service.core.interfaces import MarketBar, MarketFeedClient
from smap_service.core.retry import retry_call
from smap_service.db.provider_credentials import SQLiteProviderCredentialStore

logger = logging.getLogger(__name__)


class KotakMarketFeedClient(MarketFeedClient):
    def __init__(
        self,
        credentials: SQLiteProviderCredentialStore,
        base_url: str = "https://api.kotak.com",
        timeout_seconds: float = 5.0,
    ):
        self._credentials = credentials
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

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
        bars: list[MarketBar] = []
        for symbol in symbols:
            item = self._fetch_symbol(symbol=symbol, token=token)
            if item is not None:
                bars.append(item)
        return bars

    def _fetch_symbol(self, symbol: str, token: str) -> MarketBar | None:
        def _request() -> MarketBar | None:
            query = urllib.parse.urlencode({"symbol": symbol, "interval": "1m"})
            request = urllib.request.Request(
                f"{self._base_url}/market/bars?{query}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "User-Agent": "smap-service/0.1",
                },
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return self._normalize(symbol=symbol, payload=payload)

        try:
            return retry_call(_request, attempts=3, base_delay_seconds=0.25)
        except Exception as exc:  # pragma: no cover - network/runtime wrapper
            logger.warning("kotak fetch failed symbol=%s error=%s", symbol, exc)
            return None

    @staticmethod
    def _normalize(symbol: str, payload: dict[str, object]) -> MarketBar:
        # Baseline normalization contract; payload shape varies by provider account tier.
        return MarketBar(
            symbol=symbol,
            timeframe="1m",
            open=float(payload.get("open", 0.0)),
            high=float(payload.get("high", 0.0)),
            low=float(payload.get("low", 0.0)),
            close=float(payload.get("close", 0.0)),
            volume=int(payload.get("volume", 0)),
            as_of=str(payload.get("as_of", "")),
        )
