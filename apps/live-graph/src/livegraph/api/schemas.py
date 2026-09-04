"""Response shapes. Kept flat so the UI never has to reshape a payload."""

from __future__ import annotations

from pydantic import BaseModel


class FeedStatusOut(BaseModel):
    mode: str
    connected: bool
    instruments: int
    symbols_priced: int
    detail: str = ""


class QuoteOut(BaseModel):
    symbol: str
    ltp: float
    change_pct: float | None = None
    open_interest: int | None = None
    volume: int | None = None
    segment: str
    ts: float


class GraphNodeOut(BaseModel):
    id: str
    label: str
    name: str
    type: str
    sector: str | None = None
    fo: bool = False
    peer_groups: list[str] = []
    change_pct: float | None = None
    ltp: float | None = None


class GraphEdgeOut(BaseModel):
    source: str
    target: str
    type: str
    sign: int
    strength: float
    note: str | None = None


class GraphOut(BaseModel):
    nodes: list[GraphNodeOut]
    edges: list[GraphEdgeOut]


class EdgeProposalOut(BaseModel):
    source: str
    target: str
    correlation: float
    samples: int
    same_sector: bool
    confidence: str


class NewsItemOut(BaseModel):
    title: str
    link: str
    summary: str
    ts: float
    source: str
    entities: dict[str, str]
    fo: bool


class ImpactRowOut(BaseModel):
    symbol: str
    expected: str
    relative_magnitude: float
    hops: int
    path: str
    actual_change_pct: float | None = None


class AskIn(BaseModel):
    question: str
    thread_id: str | None = None


class AnalystReplyOut(BaseModel):
    text: str
    thread_id: str
    tools_used: list[str] = []


class ScratchpadSendIn(BaseModel):
    prompt: str
    thread_id: str | None = None


class ScratchpadTurnOut(BaseModel):
    thread_id: str
    status: str
    code: str
    explanation: str
    output: object = None
    figures: list[str] = []
    stdout: str = ""
    error: str = ""
    repairs: int = 0
    duration_ms: int = 0
