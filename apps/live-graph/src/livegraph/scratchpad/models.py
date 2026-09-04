from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class RunStatus(StrEnum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    """Everything a strategy is allowed to see, frozen at one instant.

    Passed to the sandbox as JSON, so a run is reproducible and replayable from
    the stored snapshot alone.
    """

    taken_at: float
    #: underlying -> {ltp, change_pct, open_interest, volume, segment}
    prices: dict[str, dict[str, float | str | None]] = field(default_factory=dict)
    #: underlying -> list of peer symbols
    peers: dict[str, list[str]] = field(default_factory=dict)
    #: underlying -> sector name
    sectors: dict[str, str] = field(default_factory=dict)
    #: sector name -> member symbols
    sector_members: dict[str, list[str]] = field(default_factory=dict)
    #: underlying -> [{title, ts, source}]
    news: dict[str, list[dict[str, str | float]]] = field(default_factory=dict)
    fo_symbols: list[str] = field(default_factory=list)

    def to_payload(self) -> dict:
        return {
            "taken_at": self.taken_at,
            "prices": self.prices,
            "peers": self.peers,
            "sectors": self.sectors,
            "sector_members": self.sector_members,
            "news": self.news,
            "fo_symbols": self.fo_symbols,
        }


@dataclass(frozen=True, slots=True)
class StrategyDraft:
    """Code the model produced for one turn of the conversation."""

    code: str
    explanation: str
    turn: int


@dataclass(frozen=True, slots=True)
class StrategyRun:
    status: RunStatus
    #: Whatever the strategy returned from `run(ctx)`, coerced to plain JSON.
    output: object = None
    #: Base64 PNGs of any matplotlib figures the strategy left open.
    figures: tuple[str, ...] = ()
    stdout: str = ""
    error: str = ""
    #: Traceback trimmed to the generated code's own frames.
    traceback: str = ""
    duration_ms: int = 0

    @property
    def ok(self) -> bool:
        return self.status is RunStatus.OK

    @property
    def has_figures(self) -> bool:
        return bool(self.figures)
