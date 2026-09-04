from __future__ import annotations

from dataclasses import dataclass, field


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


@dataclass(frozen=True, slots=True)
class FeedHealth:
    name: str
    ok: bool
    checked_at: float
    fetched: int = 0
    added: int = 0
    error: str | None = None
