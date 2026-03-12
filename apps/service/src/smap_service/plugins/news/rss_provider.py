from __future__ import annotations

import logging
import os
import urllib.request
import xml.etree.ElementTree as ET

from smap_service.core.interfaces import NewsItem, NewsProvider
from smap_service.core.retry import retry_call

logger = logging.getLogger(__name__)


class RSSProvider(NewsProvider):
    def __init__(self):
        feeds_raw = os.getenv(
            "SMAP_RSS_FEEDS",
            "https://www.moneycontrol.com/rss/business.xml,https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        )
        self._feeds = [item.strip() for item in feeds_raw.split(",") if item.strip()]

    @property
    def name(self) -> str:
        return "rss"

    def fetch(self) -> list[NewsItem]:
        collected: list[NewsItem] = []
        for feed_url in self._feeds:
            collected.extend(self._fetch_feed(feed_url))
        return collected

    def _fetch_feed(self, feed_url: str) -> list[NewsItem]:
        def _request() -> bytes:
            request = urllib.request.Request(
                feed_url,
                headers={"User-Agent": "smap-service/0.1"},
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=8.0) as response:
                return response.read()

        try:
            raw = retry_call(_request, attempts=3, base_delay_seconds=0.3)
        except Exception as exc:  # pragma: no cover - network/runtime wrapper
            logger.warning("rss fetch failed feed=%s error=%s", feed_url, exc)
            return []

        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return []

        items: list[NewsItem] = []
        for idx, item in enumerate(root.findall(".//item")):
            title = (item.findtext("title") or "").strip()
            if not title:
                continue
            link = (item.findtext("link") or f"{feed_url}#{idx}").strip()
            desc = (item.findtext("description") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            items.append(
                NewsItem(
                    source="rss",
                    external_id=link,
                    headline=title,
                    body=desc,
                    symbols=[],
                    published_at=pub_date,
                )
            )
        return items
