"""A feed that carries no prices.

Used when Kotak credentials are absent or a login failed. It is not a stand-in
for market data: it never emits a tick, so every price-derived surface is
visibly empty rather than quietly wrong. `FeedStatus.mode` says why.

Having an object here rather than `None` keeps the None-checks out of the rest
of the app.
"""

from __future__ import annotations

from collections.abc import Callable

from .models import Segment, Tick


class NoFeed:
    def __init__(self, reason: str):
        self.reason = reason

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def add_handler(self, handler: Callable[[Tick], None]) -> None: ...

    def remove_handler(self, handler: Callable[[Tick], None]) -> None: ...

    @property
    def is_connected(self) -> bool:
        return False

    @property
    def instrument_count(self) -> int:
        return 0

    @property
    def frames_received(self) -> int:
        return 0

    @property
    def frames_unmatched(self) -> int:
        return 0

    def latest(self, underlying: str) -> Tick | None:
        return None

    def snapshot(self, segment: Segment | None = None) -> dict[str, Tick]:
        return {}
