"""What the analyst agent is allowed to reach.

Everything the tools read comes through here, so the agent has no ambient
access to the feed, the graph or the news store.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..graph import GraphRepository
from ..news import NewsItem
from .comovement import CoMovementAnalyzer


@dataclass(frozen=True, slots=True)
class AnalystDeps:
    repo: GraphRepository
    comovement: CoMovementAnalyzer
    #: underlying -> percentage move, as of now.
    moves: Callable[[], dict[str, float]]
    #: underlying -> last traded price.
    prices: Callable[[], dict[str, float]]
    news_for: Callable[[str], list[NewsItem]]
