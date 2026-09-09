"""Sort tagged headlines into stock, sector and market scope.

The news resolver already says which graph nodes a headline mentions. This
turns that into "is this about the stock, about its neighbourhood, or about the
market", which is the distinction the drill-down is built around.

A round-up is the awkward case: it names several companies that share nothing
but the editor's list, so its tags say where a headline belongs for each name
separately and never say that those names belong together.
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
    if len(tagged) > BROAD_TAG_LIMIT or not tagged & sector_members:
        return NewsScope.MARKET
    #: A screener list drawn from across the market is not sector news just
    #: because one name in it happens to be a peer. A list that is mostly this
    #: sector — a rally in defence names, say — still is.
    companies = {node for node in tagged if not is_macro(node)}
    if item.is_roundup and not _mostly_in(companies, sector_members):
        return NewsScope.MARKET
    return NewsScope.SECTOR


def to_scoped(
    item: NewsItem,
    scope: NewsScope,
    symbol: str,
    sector_members: set[str] | frozenset[str] = frozenset(),
) -> ScopedNews:
    return ScopedNews(
        scope=scope,
        title=item.title,
        source=item.source,
        ts=item.ts,
        link=item.link,
        matched_node=_matched_node(item, scope, symbol, sector_members),
        roundup=item.is_roundup,
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
            bucket.append(to_scoped(item, scope, symbol, peers))

    ordered = (NewsScope.STOCK, NewsScope.SECTOR, NewsScope.MARKET)
    return [entry for scope in ordered for entry in buckets.get(scope, [])]


def _matched_node(
    item: NewsItem,
    scope: NewsScope,
    symbol: str,
    sector_members: set[str] | frozenset[str],
) -> str | None:
    """Which tag earned this headline its place beside `symbol`.

    In a round-up the first tag is not a stand-in for the rest, so at sector
    scope the answer has to be a name actually in the sector, and at market
    scope there is no one name that speaks for the list.
    """
    if scope is NewsScope.STOCK:
        return symbol
    if scope is NewsScope.SECTOR:
        return next((node for node in item.entities if node in sector_members), None)
    return None if item.is_roundup else next(iter(item.entities), None)


def _mostly_in(companies: set[str], sector_members: set[str] | frozenset[str]) -> bool:
    """At least half the named companies sit in the sector."""
    if not companies:
        return False
    return len(companies & set(sector_members)) * 2 >= len(companies)
