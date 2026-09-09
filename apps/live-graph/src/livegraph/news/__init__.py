"""RSS ingestion and entity resolution. Independent of `graph` and `feed`."""

from .classify import NewsKind, classify
from .models import FeedHealth, FeedSource, NewsItem
from .parser import parse_feed, strip_html
from .poller import NewsPoller
from .resolver import EntityResolver
from .sources import DEFAULT_SOURCES

__all__ = [
    "DEFAULT_SOURCES",
    "EntityResolver",
    "FeedHealth",
    "FeedSource",
    "NewsItem",
    "NewsKind",
    "NewsPoller",
    "classify",
    "parse_feed",
    "strip_html",
]
