from smap_service.core.interfaces import NewsItem, NewsProvider


class NewsAPIProvider(NewsProvider):
    @property
    def name(self) -> str:
        return "newsapi"

    def fetch(self) -> list[NewsItem]:
        # Placeholder implementation; real integration to be added in Phase 2.
        return []
