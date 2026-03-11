from typing import Any

from smap_service.core.interfaces import StrategyModule


class DefaultMomentumStrategy(StrategyModule):
    @property
    def name(self) -> str:
        return "default_momentum"

    def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Stub result for scaffolding stage.
        return {"score": 0.0, "decision": "hold", "meta": payload}
