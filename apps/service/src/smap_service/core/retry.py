from __future__ import annotations

import time
from typing import Callable, TypeVar

T = TypeVar("T")


def retry_call(
    fn: Callable[[], T],
    attempts: int = 3,
    base_delay_seconds: float = 0.25,
) -> T:
    last_exc: Exception | None = None
    for index in range(attempts):
        try:
            return fn()
        except Exception as exc:  # pragma: no cover - network path
            last_exc = exc
            if index == attempts - 1:
                break
            time.sleep(base_delay_seconds * (2**index))
    assert last_exc is not None
    raise last_exc
