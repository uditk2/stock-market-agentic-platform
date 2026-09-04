"""Backend protocol for executing generated strategy code.

One implementation today: `PyodideSandbox`, which runs strategies inside a WASM
boundary hosted by the backend itself. The protocol stays so the runtime can be
swapped without touching the scratchpad or the API.
"""

from __future__ import annotations

from typing import Protocol

from ..models import MarketSnapshot, StrategyRun


class SandboxBackend(Protocol):
    name: str

    def run(self, code: str, snapshot: MarketSnapshot) -> StrategyRun: ...

    def is_available(self) -> bool: ...

    def unavailable_reason(self) -> str: ...
