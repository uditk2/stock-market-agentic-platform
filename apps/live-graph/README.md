# livegraph

Live NSE F&O prices from Kotak Neo, overlaid on a sector/stock relationship
graph, with an agentic layer running on your existing Claude/Codex
subscriptions via CLIProxyAPI.

## Modules

Each is independently importable and tested. `feed`, `graph` and `news` do not
import one another; `api` is the only place they are joined.

| Module | Responsibility |
|---|---|
| `livegraph.feed` | Kotak Neo TOTP auth, WebSocket subscribe on `nse_fo` + `nse_cm`, scrip-master token resolution, tick normalisation. Emits `Tick`. |
| `livegraph.graph` | 545 nodes / 3003 typed edges. Symbol resolution, sector and `peer_groups` membership, signed-edge impact propagation. |
| `livegraph.news` | Polls 8 RSS sources, resolves headlines to graph node ids via `aliases.json`. |
| `livegraph.scratchpad` | Describe a strategy in English, a model writes it, it runs in an in-process WASM sandbox against a live snapshot. |
| `livegraph.llm` | Shared model access through CLIProxyAPI. |
| `livegraph.scan` | The movers scan and the per-stock drill-down: verdict classification, news scoping, web-search fallback, cached agent narration. |
| `livegraph.agent` | Co-movement edge proposals, plus an agent that answers questions through graph and price tools. |
| `livegraph.api` | FastAPI REST + WebSocket fan-out. The only layer that joins feed, graph and news. |
| `web/` | Next.js 16 + shadcn/ui dashboard: the scan drill-down, force-directed graph, scratchpad, analyst chat. Static export, served by the backend. |

Graph and alias data are vendored into `data/` from the existing `Stocks/`
project, so this app is self-contained.

## It is one application

One image, one container, one port. The backend serves the API, the WebSocket
tick feed and the UI, and hosts the strategy sandbox in-process. Nothing mounts
the Docker socket and no sibling containers are started.

```bash
cp .env.example .env      # optional; without it the simulated feed is used
docker compose up --build
```

Then open http://localhost:8000.

### Running from source instead

```bash
uv venv --python 3.13 .venv
uv pip install -e ".[dev,kotak]"
npm --prefix web install && npm --prefix web run build
npm --prefix src/livegraph/scratchpad/sandbox/worker install
LIVEGRAPH_SIMULATE=1 .venv/bin/python -m uvicorn livegraph.api.app:app --app-dir src --port 8000
```

The Kotak Neo SDK supports Python 3.10 to 3.13, so 3.13 is pinned deliberately.

### The Kotak SDK is installed without its pins

The SDK hard-pins its whole dependency tree, including `websockets==8.1` (no
Python 3.13 wheel, and it conflicts with uvicorn) and `asyncio==3.4.3`, a dead
PyPI package that shadows the standard library module. It is therefore
installed with `--no-deps`, and the `[kotak]` extra supplies the libraries it
actually imports at working versions. The Dockerfile does this already.

### Kotak credentials

Streaming needs more than the REST `access_token`. Fill these in `.env`:

| Variable | Where it comes from |
|---|---|
| `KOTAK_CONSUMER_KEY` | Neo app or web: Invest tab → Trade API card → generate application |
| `KOTAK_MOBILE_NUMBER` | Registered mobile, with country code |
| `KOTAK_UCC` | Unique Client Code, in your profile |
| `KOTAK_MPIN` | Your Neo MPIN |
| `KOTAK_TOTP_SECRET` | Base32 secret from the one-time TOTP registration |

TOTP registration is a one-time manual step at
https://www.kotaksecurities.com/platform/kotak-neo-trade-api/ (Register for
TOTP), where you scan a QR into an authenticator app.

### Model access

Agents talk OpenAI protocol to CLIProxyAPI, which fronts your Claude Code and
Codex OAuth subscriptions, so no provider API key is needed. Set
`CLIPROXY_BASE_URL` and `CLIPROXY_API_KEY` in `.env`.

**Two backend caveats, both measured not assumed:**

1. The Claude backends replace the system prompt with Claude Code's own, so a
   system-only instruction is honoured by the GPT/Codex backend and silently
   dropped by Claude. Anything that must hold on every backend goes in the
   first user message.
2. Web search works on the Anthropic-native `/v1/messages` path and on
   OpenAI's `/v1/responses`, but **not** on `/v1/chat/completions`, which the
   rest of this app uses. That path does not error, it answers without
   searching. `scan.websearch` therefore calls `/v1/messages` directly.

## Strategy sandbox

Strategy code is written by a model, so it is never executed in the backend
process. It runs inside a Pyodide (WASM) runtime hosted by a Node worker that
the backend owns. The isolation is the WASM boundary, not configuration, which
is why it needs no Docker socket and behaves identically on any host.

`jsglobals: {}` in the worker is load-bearing. Without it,
`js.globalThis.process.env` hands generated code the backend's Kotak
credentials and CLIProxy key.

Measured against the live runtime and asserted in `tests/test_scratchpad.py`:

| Escape route | Result |
|---|---|
| `js.globalThis.process.env` | unreachable |
| `pyodide.code.run_js` | unreachable |
| `js.fetch`, `micropip` | unreachable |
| `urllib` over HTTPS | no TLS available |
| raw sockets | connect cosmetically, cannot transfer a byte |
| `subprocess` | unsupported under Emscripten |
| host filesystem, `os.environ` | sandbox-local only, discarded after the run |

numpy, pandas, scipy and matplotlib are preloaded, and open figures are
captured as PNGs. The worker stays warm between runs, so a run takes a couple
of seconds rather than paying the Pyodide boot each time. WASM cannot be
interrupted, so a runaway loop is stopped by killing the worker; the next run
respawns it, and that recovery is tested.

## The repair loop

The model rarely gets a strategy right first time against unfamiliar data, so
sandbox failures are fed back as the next turn of the same conversation,
carrying the traceback with the sandbox runner's own frames stripped out.
Repairs are bounded at two, and a strategy that never succeeds is never stored.
`tests/test_scratchpad_repair.py` pins this with a scripted model so a runtime
change cannot quietly sever the feedback path.

## Tests

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q
```

Tests marked `sandbox` need Node and the worker's `node_modules`; they skip
cleanly without them.

## Simulated mode

Without Kotak credentials the app runs on a synthetic feed so the UI and API
are usable offline and out of market hours. Moves are correlated within a peer
group and again within a sector, with mean reversion so the series does not
drift onto its clamp. Every response carries `mode: "simulated"` and the header
shows an amber badge, so a generated price can never be read as a real one.

## The scan

The front door is a drill-down, not a set of parallel tabs. One list picks the
stock, and everything else hangs off it:

```
Movers                 top N each way in the F&O tier, N configurable to 100
  └─ SYMBOL            the move, the news behind it, the verdict
       ├─ Peer group   every priced peer and the gap the verdict turns on
       ├─ Sector       breadth, and every member with its own verdict
       └─ Drivers      typed graph edges, with any that disagree flagged
```

Each row carries a verdict dot, so a sector moving as a bloc reads as one story
before you open anything.

### Verdicts

Computed, never asked for. The first rule that fits wins:

| Verdict | When |
|---|---|
| Conflicted | a moving, strong graph driver points the opposite way to the price |
| Sector-wide | the move is shared with its peers, or its sector moved one-sidedly |
| Stock-specific | it stands apart from its peers, and there is stock or web news |
| Unexplained | it stands apart, and nothing accounts for it |

"Standing apart" is either a large absolute gap or a large gap relative to how
tightly the peers are clustered. A fixed threshold alone is fragile: on a quiet
session nothing ever clears it and on a volatile one everything does.

Unpriced peers are excluded from the average rather than counted as zero, which
would otherwise turn ordinary sector moves into false anomalies.

### Agent narration is cached until something changes

The model writes the closing sentence, not the verdict. A narration is reused
for the rest of the trading day unless one of the things it was based on moved:

- a new headline arrived for the stock
- the move reversed through zero, or shifted by a percentage point or more
- the deterministic verdict changed class
- it is a different trading day

The UI shows when the note was written and whether it is unchanged since, so a
cached explanation is never mistaken for a fresh one.

## Determinism boundary

Verdicts, impact propagation and co-movement correlations are plain arithmetic
in `livegraph.scan` and `livegraph.graph`. The model never computes them; it
narrates what they produced. That keeps every number on screen checkable
against the same endpoint the UI reads.

Edge proposals are candidates, never conclusions: intraday correlation is
driven by index flow as much as by any real link, so same-sector pairs are
marked low confidence and the sample count is always shown.

## Status

Working: `graph`, `news`, `scratchpad`, `agent`, `api`, and the UI, all against
the simulated feed.

Unverified: `feed` against a live Kotak session, which needs the credentials
above and an open market. The pure parts (symbol mapping, tick normalisation)
are tested; the login and socket path is not.
