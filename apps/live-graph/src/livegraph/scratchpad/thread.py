"""A scratchpad conversation: describe a strategy, get code, run it, iterate.

State lives in Pydantic AI's own message history, so each turn carries the full
thread and the model can revise its previous attempt rather than start over.
Failures are fed back in as the next user turn, which is what makes "fix it"
work without the user restating the strategy.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from ..llm import build_coder_model
from .contract import ENTRYPOINT, STRATEGY_CONTRACT
from .models import MarketSnapshot, RunStatus, StrategyDraft, StrategyRun
from .sandbox import SandboxBackend

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""\
You write Python trading-strategy code for an Indian equity F&O screener.

{STRATEGY_CONTRACT}

Put the complete function in the `code` field, as plain Python source with no
markdown fences. Everything the strategy needs goes in that one field, charting
included. Always send the whole function, never a diff or a fragment, because
it replaces the previous version wholesale.

Put a short explanation of what it does, and any assumption you had to make, in
the `explanation` field.

This is analysis tooling. Never present output as investment advice and never
invent a price you were not given in ctx.
"""

_CODE_BLOCK_RE = re.compile(r"```[A-Za-z0-9_+-]*[ \t]*\r?\n(.*?)```", re.DOTALL)
_MAX_AUTO_REPAIRS = 2


class StrategyReply(BaseModel):
    """Structured reply, so the code never has to be recovered from markdown.

    Parsing fenced blocks was unreliable in practice: models tagged fences
    inconsistently, split the function across blocks, and occasionally left a
    fence unclosed, which spliced prose into the extracted source.
    """

    code: str = Field(description="Complete Python source defining run(ctx). No markdown fences.")
    explanation: str = Field(description="One short paragraph on what it does and any assumption made.")


@dataclass
class ScratchpadTurn:
    prompt: str
    draft: StrategyDraft | None = None
    run: StrategyRun | None = None
    repairs: int = 0


@dataclass
class ScratchpadThread:
    """One conversation. Holds message history plus the last good draft."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = "Untitled strategy"
    messages: list = field(default_factory=list)
    turns: list[ScratchpadTurn] = field(default_factory=list)
    latest_code: str = ""

    @property
    def turn_count(self) -> int:
        return len(self.turns)


class ScratchpadService:
    """Owns the coding agent and the sandbox; threads are passed in per call."""

    def __init__(self, sandbox: SandboxBackend, model=None):
        from pydantic_ai import Agent

        self._sandbox = sandbox
        self._agent = Agent(
            model or build_coder_model(),
            output_type=StrategyReply,
            system_prompt=SYSTEM_PROMPT,
            retries=2,
        )

    async def send(
        self,
        thread: ScratchpadThread,
        prompt: str,
        snapshot: MarketSnapshot,
        auto_repair: bool = True,
    ) -> ScratchpadTurn:
        """One user turn: generate code, run it, and retry on failure."""
        turn = ScratchpadTurn(prompt=prompt)
        thread.turns.append(turn)

        framed = prompt if thread.messages else self._opening_turn(prompt, snapshot)
        turn.draft = await self._generate(thread, framed)
        turn.run = self._sandbox.run(turn.draft.code, snapshot)

        while auto_repair and not turn.run.ok and turn.repairs < _MAX_AUTO_REPAIRS:
            turn.repairs += 1
            logger.info("scratchpad %s: repair %d", thread.id, turn.repairs)
            turn.draft = await self._generate(thread, _repair_prompt(turn.run))
            turn.run = self._sandbox.run(turn.draft.code, snapshot)

        if turn.run.ok:
            thread.latest_code = turn.draft.code
        return turn

    async def rerun(
        self, thread: ScratchpadThread, snapshot: MarketSnapshot
    ) -> StrategyRun:
        """Re-execute the last working strategy against a fresh snapshot.

        No model call, so the same strategy can be polled cheaply as prices move.
        """
        if not thread.latest_code:
            return StrategyRun(
                status=RunStatus.REJECTED, error="this thread has no working strategy yet"
            )
        return self._sandbox.run(thread.latest_code, snapshot)

    @staticmethod
    def _opening_turn(prompt: str, snapshot: MarketSnapshot) -> str:
        """Carry the contract in the first user message, not only the system prompt.

        CLIProxyAPI's Claude backends replace the system prompt with Claude
        Code's own, so a system-only contract reaches GPT but never Claude.
        Restating it here makes the scratchpad behave the same on either.
        """
        return (
            f"{SYSTEM_PROMPT}\n\n"
            f"{describe_snapshot(snapshot)}\n\n"
            f"The strategy to write:\n{prompt}"
        )

    async def _generate(self, thread: ScratchpadThread, prompt: str) -> StrategyDraft:
        result = await self._agent.run(prompt, message_history=thread.messages)
        thread.messages = result.all_messages()
        reply = result.output
        return StrategyDraft(
            #: Models still fence the field's contents now and then, so unwrap
            #: defensively rather than failing the whole turn on it.
            code=extract_code(reply.code) or reply.code.strip(),
            explanation=reply.explanation.strip(),
            turn=thread.turn_count,
        )


def describe_snapshot(snapshot: MarketSnapshot) -> str:
    """A compact, factual preview of the ctx the strategy will receive."""
    sample = next(iter(snapshot.prices.items()), None)
    example = f"{sample[0]} -> {sample[1]}" if sample else "none yet"
    return (
        "This run's ctx contains:\n"
        f"  ctx.prices: {len(snapshot.prices)} symbols, e.g. {example}\n"
        f"  ctx.peers: {len(snapshot.peers)} symbols with peer lists\n"
        f"  ctx.sectors: {len(snapshot.sectors)} symbols mapped to sectors\n"
        f"  ctx.sector_members: {len(snapshot.sector_members)} sectors\n"
        f"  ctx.news: {len(snapshot.news)} symbols with headlines\n"
        f"  ctx.fo_symbols: {len(snapshot.fo_symbols)} F&O symbols"
    )


def extract_code(text: str) -> str:
    """Pull the strategy out of the reply.

    Replies routinely carry several fenced blocks: the function, then a sample
    of its output or a fragment being discussed. Taking the last block blindly
    picks the wrong one and burns a repair round, so prefer the last block that
    actually defines the entrypoint.
    """
    blocks = [block.strip() for block in _CODE_BLOCK_RE.findall(text)]
    entrypoints = [block for block in blocks if f"def {ENTRYPOINT}(" in block]
    if entrypoints:
        return entrypoints[-1]
    if blocks:
        return blocks[-1]
    #: Some models skip the fence when the reply is code and nothing else.
    return text.strip() if f"def {ENTRYPOINT}(" in text else ""


def strip_code_blocks(text: str) -> str:
    return _CODE_BLOCK_RE.sub("", text).strip()


def _repair_prompt(run: StrategyRun) -> str:
    detail = run.traceback or run.error
    if run.status is RunStatus.TIMEOUT:
        return (
            "That strategy hit the execution timeout. Rewrite it to finish quickly: "
            "remove unbounded loops and avoid work that scales with every symbol pair."
        )
    if run.status is RunStatus.REJECTED:
        return f"That code was rejected before it ran: {run.error}. Fix it and resend the whole function."
    return (
        f"That strategy failed when it ran:\n\n{detail}\n\n"
        "Fix the cause and resend the complete function. Remember that many "
        "symbols have no price, so guard every lookup."
    )
