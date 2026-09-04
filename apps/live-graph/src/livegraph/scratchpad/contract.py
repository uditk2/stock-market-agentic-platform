"""The interface generated strategy code must satisfy.

`STRATEGY_CONTRACT` is injected into the model's system prompt verbatim, so
what the model is told and what the sandbox provides cannot drift apart.
"""

from __future__ import annotations

ENTRYPOINT = "run"

AVAILABLE_LIBRARIES = ("numpy", "pandas", "scipy", "matplotlib")

STRATEGY_CONTRACT = '''\
Write a single Python function with this exact signature:

    def run(ctx) -> dict:

`ctx` is a read-only snapshot of the market, taken the moment the strategy ran:

    ctx.prices          dict[str, dict]  underlying -> {"ltp": float,
                                          "change_pct": float | None,
                                          "open_interest": int | None,
                                          "volume": int | None,
                                          "segment": "nse_fo" | "nse_cm"}
    ctx.peers           dict[str, list[str]]  underlying -> tight competitor symbols
    ctx.sectors         dict[str, str]        underlying -> sector name
    ctx.sector_members  dict[str, list[str]]  sector name -> member symbols
    ctx.news            dict[str, list[dict]] underlying -> [{"title","ts","source"}]
    ctx.fo_symbols      list[str]             symbols in the F&O (screenable) tier
    ctx.taken_at        float                 snapshot epoch seconds

Available libraries: numpy, pandas, scipy, matplotlib (plus the standard
library). The code runs in an offline container, so there is no network and
nothing else can be installed.

`ctx` is a plain namespace with exactly the attributes listed above. It is not
a DataFrame and it is not a dict. Do not write code that searches it for other
shapes or falls back to alternative attribute names; anything not listed above
does not exist. Build your own DataFrame from ctx.prices if you want one.

A correct, complete answer looks like this:

    def run(ctx):
        rows = []
        for symbol, peers in ctx.peers.items():
            own = (ctx.prices.get(symbol) or {}).get("change_pct")
            moves = [
                (ctx.prices.get(p) or {}).get("change_pct")
                for p in peers
                if (ctx.prices.get(p) or {}).get("change_pct") is not None
            ]
            if own is None or not moves:
                continue
            peer_avg = sum(moves) / len(moves)
            rows.append({"symbol": symbol, "change_pct": own,
                         "peer_avg": peer_avg, "gap": own - peer_avg})
        rows.sort(key=lambda r: -abs(r["gap"]))
        return {"rows": rows[:5]}

Rules:
- Return a JSON-serialisable dict. numpy and pandas values are converted for
  you, so returning a DataFrame inside the dict is fine.
- Put ranked results under a "rows" key so the UI can render them as a table.
- When a chart is asked for, DRAW IT with matplotlib. Build the figure and
  leave it open; every open figure is captured as a PNG and displayed for you.
  Do not call plt.show() and do not call plt.savefig() - saving is unnecessary
  and the filesystem is ephemeral.
- Never return chart data, a chart spec, or a "charts" key instead of drawing.
  Nothing renders such a structure; an undrawn chart is simply a missing chart.
- Not every symbol has a price; missing keys are normal, so use .get().
- Return what you want to see; stdout is captured for debugging only.
- No infinite loops. The container is killed after a hard timeout.
'''

#: Imports that would bridge out of the sandbox. Everything else is permitted,
#: because the container is the security boundary, not this list.
BLOCKED_IMPORTS: frozenset[str] = frozenset({"ctypes", "multiprocessing"})
