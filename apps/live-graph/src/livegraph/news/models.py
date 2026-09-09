from __future__ import annotations

from dataclasses import dataclass, field

from .classify import NewsKind


@dataclass(frozen=True, slots=True)
class FeedSource:
    name: str
    url: str


@dataclass(slots=True)
class NewsItem:
    title: str
    link: str
    summary: str
    ts: float
    source: str = ""
    #: node id -> the alias text that matched it
    entities: dict[str, str] = field(default_factory=dict)
    fo: bool = False
    #: Whether the item is one story or a list of several filed together, which
    #: decides whether its tags may be read as names that belong beside one
    #: another. See `classify`.
    kind: NewsKind = NewsKind.SINGLE

    @property
    def is_roundup(self) -> bool:
        return self.kind is NewsKind.ROUNDUP


@dataclass(frozen=True, slots=True)
class FeedHealth:
    name: str
    ok: bool
    checked_at: float
    fetched: int = 0
    added: int = 0
    error: str | None = None
