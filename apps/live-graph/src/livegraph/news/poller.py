"""Fetch RSS sources on an interval and keep a de-duplicated, tagged store."""

from __future__ import annotations

import logging
import time
import urllib.error
import urllib.request
from collections.abc import Callable

from .models import FeedHealth, FeedSource, NewsItem
from .parser import parse_feed
from .resolver import EntityResolver
from .sources import DEFAULT_SOURCES, USER_AGENT

logger = logging.getLogger(__name__)

DEFAULT_POLL_SECONDS = 300
DEFAULT_KEEP_ITEMS = 3000
_FETCH_TIMEOUT = 20


class NewsPoller:
    def __init__(
        self,
        resolver: EntityResolver,
        is_fo: Callable[[str], bool],
        sources: tuple[FeedSource, ...] = DEFAULT_SOURCES,
        keep_items: int = DEFAULT_KEEP_ITEMS,
    ):
        self._resolver = resolver
        self._is_fo = is_fo
        self._sources = sources
        self._keep_items = keep_items
        self._items: dict[str, NewsItem] = {}
        self._health: dict[str, FeedHealth] = {}

    def poll_once(self) -> list[NewsItem]:
        """Fetch every source once. Returns only the items new to this store."""
        added: list[NewsItem] = []
        for source in self._sources:
            added.extend(self._poll_source(source))
        self._trim()
        return added

    def _poll_source(self, source: FeedSource) -> list[NewsItem]:
        try:
            raw = self._fetch(source.url)
            fetched = parse_feed(raw)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            self._health[source.name] = FeedHealth(
                name=source.name, ok=False, checked_at=time.time(), error=str(exc)[:120]
            )
            logger.warning("feed %s failed: %s", source.name, exc)
            return []

        added = [self._ingest(item, source.name) for item in fetched]
        new_items = [item for item in added if item is not None]
        self._health[source.name] = FeedHealth(
            name=source.name,
            ok=True,
            checked_at=time.time(),
            fetched=len(fetched),
            added=len(new_items),
        )
        return new_items

    def _ingest(self, item: NewsItem, source_name: str) -> NewsItem | None:
        if item.link in self._items:
            return None
        item.source = source_name
        item.entities = self._resolver.resolve(f"{item.title} {item.summary}")
        item.fo = any(self._is_fo(node_id) for node_id in item.entities)
        self._items[item.link] = item
        return item

    def _fetch(self, url: str) -> bytes:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=_FETCH_TIMEOUT) as response:
            return response.read()

    def _trim(self) -> None:
        if len(self._items) <= self._keep_items:
            return
        newest = sorted(self._items.values(), key=lambda i: -i.ts)[: self._keep_items]
        self._items = {item.link: item for item in newest}

    # ---- read access -------------------------------------------------

    def recent(self, limit: int = 100, fo_only: bool = False) -> list[NewsItem]:
        items = sorted(self._items.values(), key=lambda i: -i.ts)
        if fo_only:
            items = [item for item in items if item.fo]
        return items[:limit]

    def for_node(self, node_id: str, limit: int = 20) -> list[NewsItem]:
        tagged = [item for item in self._items.values() if node_id in item.entities]
        return sorted(tagged, key=lambda i: -i.ts)[:limit]

    @property
    def health(self) -> dict[str, FeedHealth]:
        return dict(self._health)
