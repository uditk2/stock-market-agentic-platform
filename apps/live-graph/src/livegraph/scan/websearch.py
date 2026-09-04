"""Fill a news gap by searching the web.

Used only when the tagged RSS feeds carry nothing for a symbol, because a
missing headline is otherwise indistinguishable from a genuinely quiet name,
and the verdict turns on that difference.

Endpoint note, measured against a live CLIProxyAPI: web search works on the
Anthropic-native `/v1/messages` path and on OpenAI's `/v1/responses`, but NOT
on `/v1/chat/completions`, which the rest of this app uses. That path does not
error, it just answers without searching. This client therefore talks to
`/v1/messages` directly rather than going through the shared OpenAI provider.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from ..llm import get_llm_settings
from .models import NewsScope, ScopedNews

logger = logging.getLogger(__name__)

SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 2}
DEFAULT_TIMEOUT = 90
DEFAULT_TTL_SECONDS = 600
MAX_RESULTS = 3

PROMPT = """\
Search for news published in the last two days about {symbol} ({name}), an \
Indian listed company in the {sector} sector, or about that sector.

Reply with a JSON array and nothing else. At most {limit} entries, each:
{{"title": "...", "source": "...", "url": "..."}}

Only include items you actually found in the search results, with the real \
publisher name and the real URL. Return [] if there is nothing from the last \
two days. Never invent a headline.
"""


@dataclass
class _Entry:
    items: list[ScopedNews]
    at: float


class WebNewsSearch:
    """Cached, best-effort web lookups. Never raises into the request path."""

    def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self._timeout = timeout_seconds
        self._ttl = ttl_seconds
        self._cache: dict[str, _Entry] = {}

    def is_configured(self) -> bool:
        return bool(get_llm_settings().cliproxy_api_key)

    def search(self, symbol: str, name: str, sector: str | None) -> list[ScopedNews]:
        cached = self._cache.get(symbol)
        if cached and time.monotonic() - cached.at < self._ttl:
            return cached.items

        items = self._fetch(symbol, name, sector or "Indian equity")
        self._cache[symbol] = _Entry(items=items, at=time.monotonic())
        return items

    def _fetch(self, symbol: str, name: str, sector: str) -> list[ScopedNews]:
        try:
            payload = self._call(
                PROMPT.format(symbol=symbol, name=name, sector=sector, limit=MAX_RESULTS)
            )
        except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
            logger.warning("web search for %s failed: %s", symbol, exc)
            return []
        return self._to_news(payload)

    def _call(self, prompt: str) -> str:
        settings = get_llm_settings()
        body = json.dumps({
            "model": settings.livegraph_agent_model,
            "max_tokens": 1200,
            "tools": [SEARCH_TOOL],
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")

        request = urllib.request.Request(
            _messages_url(settings.cliproxy_base_url),
            data=body,
            headers={
                "x-api-key": settings.cliproxy_api_key or "cliproxy-local",
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        #: The reply interleaves thinking, tool calls and several text blocks.
        return "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )

    @staticmethod
    def _to_news(text: str) -> list[ScopedNews]:
        rows = _parse_json_array(text)
        now = time.time()
        return [
            ScopedNews(
                scope=NewsScope.WEB,
                title=str(row.get("title", "")).strip()[:300],
                source=f"web · {str(row.get('source', 'unknown')).strip()[:60]}",
                ts=now,
                link=str(row.get("url", "")).strip(),
            )
            for row in rows[:MAX_RESULTS]
            if str(row.get("title", "")).strip()
        ]


def _messages_url(base_url: str) -> str:
    """/v1/... on the proxy; the shared setting points at the OpenAI-compat root."""
    return base_url.rstrip("/") + "/messages"


def _parse_json_array(text: str) -> list[dict]:
    """Take the JSON array out of a reply that may wrap it in prose or a fence."""
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end <= start:
        return []
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    return [row for row in parsed if isinstance(row, dict)] if isinstance(parsed, list) else []
