from smap_service.core.interfaces import NewsItem, NewsProvider


class RSSProvider(NewsProvider):
    @property
    def name(self) -> str:
        return "rss"

    def fetch(self) -> list[NewsItem]:
        # Placeholder implementation for RSS ingestion.
        return []
