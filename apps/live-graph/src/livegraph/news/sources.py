"""RSS sources. Carried over from the original news_feed.py feed list."""

from __future__ import annotations

from .models import FeedSource

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124 Safari/537.36"
)

DEFAULT_SOURCES: tuple[FeedSource, ...] = (
    FeedSource("Moneycontrol Markets", "https://www.moneycontrol.com/rss/marketreports.xml"),
    FeedSource("Moneycontrol Business", "https://www.moneycontrol.com/rss/business.xml"),
    FeedSource("Moneycontrol Latest", "https://www.moneycontrol.com/rss/latestnews.xml"),
    FeedSource("ET Markets", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    FeedSource("ET Top Stories", "https://economictimes.indiatimes.com/rssfeedstopstories.cms"),
    FeedSource("Livemint Markets", "https://www.livemint.com/rss/markets"),
    FeedSource("Livemint Companies", "https://www.livemint.com/rss/companies"),
    FeedSource("Business Standard Mkts", "https://www.business-standard.com/rss/markets-106.rss"),
)
