from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


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


class StrategyModule(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
