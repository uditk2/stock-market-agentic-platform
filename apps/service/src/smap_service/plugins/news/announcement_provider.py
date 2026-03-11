from smap_service.core.interfaces import NewsItem, NewsProvider


class NSEAnnouncementProvider(NewsProvider):
    @property
    def name(self) -> str:
        return "nse_announcements"

    def fetch(self) -> list[NewsItem]:
        return []
