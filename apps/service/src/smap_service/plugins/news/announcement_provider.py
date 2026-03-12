from __future__ import annotations

import json
import logging
import urllib.request

from smap_service.core.interfaces import NewsItem, NewsProvider
from smap_service.core.retry import retry_call

logger = logging.getLogger(__name__)


class NSEAnnouncementProvider(NewsProvider):
    def __init__(
        self,
        endpoint: str = "https://www.nseindia.com/api/corporate-announcements",
    ):
        self._endpoint = endpoint

    @property
    def name(self) -> str:
        return "nse_announcements"

    def fetch(self) -> list[NewsItem]:
        def _request() -> list[NewsItem]:
            request = urllib.request.Request(
                self._endpoint,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; smap-service/0.1)",
                    "Accept": "application/json",
                },
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=8.0) as response:
                payload = json.loads(response.read().decode("utf-8"))

            items: list[NewsItem] = []
            for idx, row in enumerate(payload):
                title = str(row.get("subject", "")).strip()
                if not title:
                    continue
                symbol = str(row.get("symbol", "")).strip()
                items.append(
                    NewsItem(
                        source="nse_announcements",
                        external_id=str(row.get("an_dt", f"nse-{idx}")),
                        headline=title,
                        body=str(row.get("desc", "")),
                        symbols=[symbol] if symbol else [],
                        published_at=str(row.get("an_dt", "")),
                    )
                )
            return items

        try:
            return retry_call(_request, attempts=3, base_delay_seconds=0.4)
        except Exception as exc:  # pragma: no cover - network/runtime wrapper
            logger.warning("nse announcements fetch failed: %s", exc)
            return []
