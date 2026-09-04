"""The graph-aware analyst agent.

Tools do all the arithmetic; the model's job is to choose them, read the graph
paths and say plainly what does and does not hold. Threads are Pydantic AI
message histories, so a follow-up question keeps its context.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from pydantic_ai import RunContext

from ..llm import build_analyst_model
from . import tools
from .deps import AnalystDeps
from .prompts import ANALYST_INSTRUCTIONS


@dataclass
class AnalystThread:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    messages: list = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class AnalystReply:
    text: str
    thread_id: str
    #: Names of the tools the model actually called, so the UI can show its work.
    tools_used: tuple[str, ...] = ()


class AnalystService:
    def __init__(self, deps: AnalystDeps, model=None):
        from pydantic_ai import Agent

        self._deps = deps
        self._agent = Agent(
            model or build_analyst_model(),
            deps_type=AnalystDeps,
            system_prompt=ANALYST_INSTRUCTIONS,
            retries=2,
        )
        self._register_tools()

    def _register_tools(self) -> None:
        """Each tool is declared with an explicit signature.

        Pydantic AI builds the tool schema from type hints, so a generic
        **kwargs wrapper registers a tool the model cannot call.
        """
        agent = self._agent

        @agent.tool
        def quote(ctx: RunContext[AnalystDeps], symbol: str) -> dict:
            """Last price and percentage move for one symbol."""
            return tools.quote(ctx.deps, symbol)

        @agent.tool
        def top_movers(
            ctx: RunContext[AnalystDeps], direction: str = "both", limit: int = 10
        ) -> dict:
            """Largest movers right now. direction is 'up', 'down' or 'both'."""
            return tools.top_movers(ctx.deps, direction, limit)

        @agent.tool
        def neighbours(ctx: RunContext[AnalystDeps], symbol: str) -> dict:
            """Nodes directly connected to symbol, with edge type, sign and live move."""
            return tools.neighbours(ctx.deps, symbol)

        @agent.tool
        def peer_comparison(ctx: RunContext[AnalystDeps], symbol: str) -> dict:
            """How symbol is moving against its peer group and its sector."""
            return tools.peer_comparison(ctx.deps, symbol)

        @agent.tool
        def propagate_impact(
            ctx: RunContext[AnalystDeps], origin: str, direction: str = "up"
        ) -> dict:
            """Rank what the graph says is affected when origin moves up or down.

            origin may be a stock or a macro node such as CRUDE or USDINR.
            """
            return tools.propagate_impact(ctx.deps, origin, direction)


        @agent.tool
        def recent_news(ctx: RunContext[AnalystDeps], symbol: str, limit: int = 5) -> dict:
            """Headlines already tagged to symbol by the news resolver."""
            return tools.recent_news(ctx.deps, symbol, limit)

        @agent.tool
        def proposed_edges(ctx: RunContext[AnalystDeps], limit: int = 10) -> dict:
            """Correlated pairs the graph does not connect. Candidates, not conclusions."""
            return tools.proposed_edges(ctx.deps, limit)

    async def ask(self, thread: AnalystThread, question: str) -> AnalystReply:
        #: The instructions ride in the first user turn too, because the Claude
        #: backend behind CLIProxyAPI discards the system prompt.
        framed = question if thread.messages else f"{ANALYST_INSTRUCTIONS}\n\nQuestion:\n{question}"
        result = await self._agent.run(framed, deps=self._deps, message_history=thread.messages)
        thread.messages = result.all_messages()
        return AnalystReply(
            text=result.output,
            thread_id=thread.id,
            tools_used=_tool_names(result.all_messages()),
        )

    async def explain(self, thread: AnalystThread, symbol: str) -> AnalystReply:
        """Why is this stock moving, in graph terms?"""
        return await self.ask(
            thread,
            f"{symbol} is moving. Using the tools, explain what the graph says about it: "
            f"its own move, how it compares with its peers and sector, which connected "
            f"nodes are moving, and any tagged news. State clearly if the graph does not "
            f"explain the move.",
        )

    async def review_edge_proposals(self, thread: AnalystThread) -> AnalystReply:
        return await self.ask(
            thread,
            "Call proposed_edges. For each candidate, say whether a real economic link "
            "plausibly exists (supplier, competitor, shared input) or whether shared index "
            "flow explains it. Recommend accept or reject per pair, with the edge type and "
            "sign you would use if accepted. Say when you are unsure.",
        )


def _tool_names(messages: list) -> tuple[str, ...]:
    names: list[str] = []
    for message in messages:
        for part in getattr(message, "parts", ()):
            name = getattr(part, "tool_name", None)
            if name and name not in names:
                names.append(name)
    return tuple(names)
