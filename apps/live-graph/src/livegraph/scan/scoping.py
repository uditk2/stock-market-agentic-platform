"""Sort tagged headlines into stock, sector and market scope.

The news resolver already says which graph nodes a headline mentions. This
turns that into "is this about the stock, about its neighbourhood, or about the
market", which is the distinction the drill-down is built around.
"""

from __future__ import annotations

from collections.abc import Callable

from ..news import NewsItem
from .models import NewsScope, ScopedNews

#: More than this many tagged names and the headline is a market round-up
#: rather than a story about any one of them.
BROAD_TAG_LIMIT = 6


def scope_for(
    item: NewsItem,
    symbol: str,
    sector_members: set[str],
    is_macro: Callable[[str], bool],
) -> NewsScope:
    """Narrowest scope that fits. A stock hit always beats a sector hit."""
    tagged = set(item.entities)
    if symbol in tagged:
        return NewsScope.STOCK
    if len(tagged) > BROAD_TAG_LIMIT:
        return NewsScope.MARKET
    if tagged & sector_members:
        return NewsScope.SECTOR
    if any(is_macro(node) for node in tagged):
        return NewsScope.MARKET
    return NewsScope.MARKET


def to_scoped(item: NewsItem, scope: NewsScope, symbol: str) -> ScopedNews:
    matched = symbol if scope is NewsScope.STOCK else next(iter(item.entities), None)
    return ScopedNews(
        scope=scope,
        title=item.title,
        source=item.source,
        ts=item.ts,
        link=item.link,
        matched_node=matched,
    )


def collect(
    items: list[NewsItem],
    symbol: str,
    sector_members: set[str],
    is_macro: Callable[[str], bool],
    per_scope_limit: int = 3,
) -> list[ScopedNews]:
    """Scope every headline, newest first, capped per scope.

    Capping per scope rather than overall keeps one noisy market round-up from
    crowding out the single stock-level headline that actually matters.
    """
    peers = sector_members - {symbol}
    buckets: dict[NewsScope, list[ScopedNews]] = {}
    for item in sorted(items, key=lambda i: -i.ts):
        scope = scope_for(item, symbol, peers, is_macro)
        bucket = buckets.setdefault(scope, [])
        if len(bucket) < per_scope_limit:
            bucket.append(to_scoped(item, scope, symbol))

    ordered = (NewsScope.STOCK, NewsScope.SECTOR, NewsScope.MARKET)
    return [entry for scope in ordered for entry in buckets.get(scope, [])]
