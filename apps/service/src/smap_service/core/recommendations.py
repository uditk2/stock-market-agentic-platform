from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class Recommendation:
    recommendation_id: str
    symbol: str
    confidence: float
    direction: str
    summary: str
    tabs: dict[str, list[str]]


class RecommendationService:
    def __init__(self):
        self._items: list[Recommendation] = [
            Recommendation(
                recommendation_id="rec-1",
                symbol="RELIANCE-FUT",
                confidence=0.88,
                direction="long",
                summary="Momentum with supportive earnings commentary.",
                tabs={
                    "news": [
                        "Positive management guidance commentary",
                        "Sector demand outlook improved in last 24h",
                    ],
                    "technicals": [
                        "Price above 20/50 EMA",
                        "RSI near 61 with rising volume",
                    ],
                    "strategy": [
                        "Default momentum module score is positive",
                        "Risk/reward above configured threshold",
                    ],
                },
            ),
            Recommendation(
                recommendation_id="rec-2",
                symbol="TCS-FUT",
                confidence=0.81,
                direction="long",
                summary="Trend continuation with moderate volatility.",
                tabs={
                    "news": ["Large-deal pipeline updates remain constructive"],
                    "technicals": ["Higher-high / higher-low sequence intact"],
                    "strategy": ["Signal persistence across two intervals"],
                },
            ),
            Recommendation(
                recommendation_id="rec-3",
                symbol="INFY-FUT",
                confidence=0.74,
                direction="short",
                summary="Weak short-term momentum with negative breadth.",
                tabs={
                    "news": ["Muted discretionary spending signals from peers"],
                    "technicals": ["Break below short-term support band"],
                    "strategy": ["Downside breakout criteria met"],
                },
            ),
        ]

    def list(self, query: str | None = None) -> list[Recommendation]:
        filtered = self._items
        if query:
            q = query.strip().lower()
            filtered = [item for item in filtered if q in item.symbol.lower()]
        return sorted(filtered, key=lambda item: item.confidence, reverse=True)

    def get(self, recommendation_id: str) -> Recommendation | None:
        for item in self._items:
            if item.recommendation_id == recommendation_id:
                return item
        return None

    @staticmethod
    def to_dict(item: Recommendation) -> dict[str, object]:
        return asdict(item)
