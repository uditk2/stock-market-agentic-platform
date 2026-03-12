from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request

from smap_service.core.interfaces import NewsItem, NewsProvider
from smap_service.core.retry import retry_call

logger = logging.getLogger(__name__)


class NewsAPIProvider(NewsProvider):
    def __init__(self, endpoint: str = "https://newsapi.org/v2/everything"):
        self._endpoint = endpoint

    @property
    def name(self) -> str:
        return "newsapi"

    def fetch(self) -> list[NewsItem]:
        api_key = os.getenv("SMAP_NEWSAPI_KEY")
        if not api_key:
            logger.info("newsapi skipped: missing SMAP_NEWSAPI_KEY")
            return []

        def _request() -> list[NewsItem]:
            query = urllib.parse.urlencode(
                {
                    "q": "NSE OR futures OR options",
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": "20",
                }
            )
            request = urllib.request.Request(
                f"{self._endpoint}?{query}",
                headers={"X-Api-Key": api_key, "User-Agent": "smap-service/0.1"},
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=8.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
            items: list[NewsItem] = []
            for idx, article in enumerate(payload.get("articles", [])):
                title = str(article.get("title", "")).strip()
                if not title:
                    continue
                description = str(article.get("description", "")).strip()
                source_name = str(article.get("source", {}).get("name", "newsapi"))
                items.append(
                    NewsItem(
                        source=source_name,
                        external_id=str(article.get("url", f"newsapi-{idx}")),
                        headline=title,
                        body=description,
                        symbols=[],
                        published_at=str(article.get("publishedAt", "")),
                    )
                )
            return items

        try:
            return retry_call(_request, attempts=3, base_delay_seconds=0.4)
        except Exception as exc:  # pragma: no cover - network/runtime wrapper
            logger.warning("newsapi fetch failed: %s", exc)
            return []
