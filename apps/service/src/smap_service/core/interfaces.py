from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class MarketBar:
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    as_of: str


@dataclass
class NewsItem:
    source: str
    external_id: str
    headline: str
    body: str
    symbols: list[str]
    published_at: str


class LLMAdapter(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def summarize(self, text: str) -> str:
        raise NotImplementedError


class NewsProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def fetch(self) -> list[NewsItem]:
        raise NotImplementedError


class MarketFeedClient(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def fetch_latest_bars(self, symbols: list[str]) -> list[MarketBar]:
        raise NotImplementedError


class StrategyModule(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
