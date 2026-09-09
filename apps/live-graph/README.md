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
docker compose up --build
```

Then open http://localhost:8000. Nothing needs configuring first: the app
starts, serves the graph, and the Admin tab says what is missing.

There are two things to set up, and the Admin tab handles both: Kotak
credentials go into a form there, and model access is a login against
CLIProxyAPI, which owns that flow and ships its own control panel.

The tab is behind a passphrase, so set one in `.env` first — without it the
tab shows only an explanation of how to enable it:

```
LIVEGRAPH_ADMIN_PASSWORD=something-only-you-know
```

See [Admin](#admin).

If you would rather not type credentials into a browser at all,
`./scripts/setup-kotak.sh` fills `.env` with terminal echo off, printing
nothing.

### A proxy of your own

`CLIPROXY_BASE_URL` defaults to a proxy on the host, because one CLIProxyAPI is
usually shared across projects. On a machine with none:

```bash
docker compose --profile local-proxy up --build
docker compose --profile local-proxy exec cliproxy ./CLIProxyAPI -claude-login
docker compose --profile local-proxy exec cliproxy ./CLIProxyAPI -codex-device-login
```

The logins open OAuth flows against subscriptions you already have; no provider
API key is involved. Tokens land in the `cliproxy-auths` volume and survive
rebuilds. Change the placeholder key in `cliproxy/config.yaml` and put the same
value in `CLIPROXY_API_KEY`.

The profile is opt-in rather than the default for one reason: those tokens are
long-lived grants on your personal accounts, and two proxies signed into the
same account keep two token stores and refresh them independently, which can
invalidate each other. If a proxy is already running, leave the profile off and
point `LIVEGRAPH_CLIPROXY_URL` at it.

### Running from source instead

```bash
uv venv --python 3.13 .venv
uv pip install -e ".[dev,kotak]"
npm --prefix web install && npm --prefix web run build
npm --prefix src/livegraph/scratchpad/sandbox/worker install
.venv/bin/python -m uvicorn livegraph.api.app:app --app-dir src --port 8000
```

The Kotak Neo SDK supports Python 3.10 to 3.13, so 3.13 is pinned deliberately.

### The Kotak SDK is installed without its pins

The SDK hard-pins its whole dependency tree, including `websockets==8.1` (no
Python 3.13 wheel, and it conflicts with uvicorn) and `asyncio==3.4.3`, a dead
PyPI package that shadows the standard library module. It is therefore
installed with `--no-deps`, and the `[kotak]` extra supplies the libraries it
actually imports at working versions. The Dockerfile does this already.

### Kotak credentials

Streaming needs more than the REST `access_token`. Two helpers fill `.env`,
both reading with terminal echo off so nothing reaches your scrollback:

```bash
./scripts/import-kotak-from-smap.sh   # recover what the old platform stored
./scripts/setup-kotak.sh              # enter the rest by hand
```

The fields:

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

### Checking the Kotak path

A failed feed reports one line — `Kotak login failed: ...` — which is enough to
know something is wrong and not enough to fix it. `./scripts/check-kotak.py`
runs the same path in stages and names the first that fails, so a wrong MPIN is
distinguishable from clock skew, an unregistered TOTP, or a closed market:

```bash
./scripts/check-kotak.py                # use .env and whatever Admin stored
./scripts/check-kotak.py --prompt       # type the missing ones, in memory only
./scripts/check-kotak.py --prompt --save   # ...and keep them
./scripts/check-kotak.py --totp 123456  # supply the code non-interactively
./scripts/check-kotak.py --skip-socket  # stop after the REST checks
```

**It needs no TOTP secret.** Kotak's API takes the six-digit code, never the
secret; storing the secret is only how the app logs itself back in each
morning. With no usable secret configured the script asks for the code, which
is also the only route open when a stored secret turns out to be wrong.

It also names the two values that are usually the wrong thing entirely — a
mobile number without its country code, and a six-digit code pasted where the
base32 secret belongs. Both pass every presence check and fail at Kotak as an
unexplained rejection.

It goes through `livegraph.feed` rather than the SDK, so a pass means the app
works rather than that the SDK does, and it prints no credential — fields are
reported by presence, length and origin. It re-runs itself under `.venv` and
normalises the working directory, so it behaves the same from anywhere.

Outside 09:15-15:30 IST the socket connects and stays quiet. That is a pass
with zero ticks, and the script says so rather than calling it a failure.

### Model access

Agents talk OpenAI protocol to CLIProxyAPI, which fronts your Claude Code and
Codex OAuth subscriptions, so no provider API key is needed. Set
`CLIPROXY_BASE_URL` and `CLIPROXY_API_KEY` in `.env`, or run one with the
`local-proxy` profile above.

The Admin tab probes `/v1/models` and reports three states apart: nothing
listening, listening but rejecting the key, and working — plus whether the
proxy actually advertises the two models this app asks for. A proxy that is up
with no Claude credential loaded answers happily without them, which is the
failure worth catching early.

Provider logins are not reimplemented here. They belong to CLIProxyAPI
(`-claude-login`, `-codex-device-login`), it serves a control panel at
`/management.html` that drives them, and the Admin tab links to it.

**Two backend caveats, both measured not assumed:**

1. The Claude backends replace the system prompt with Claude Code's own, so a
   system-only instruction is honoured by the GPT/Codex backend and silently
   dropped by Claude. Anything that must hold on every backend goes in the
   first user message.
2. Web search works on the Anthropic-native `/v1/messages` path and on
   OpenAI's `/v1/responses`, but **not** on `/v1/chat/completions`, which the
   rest of this app uses. That path does not error, it answers without
   searching. `scan.websearch` therefore calls `/v1/messages` directly.

## Admin

The tab that exists so a fresh `docker compose up` is enough. It reports the
broker session, the Kotak credentials, the current TOTP code and the state of
model access, and it can change the first two.

**The whole tab is behind a passphrase**, reads included. Set
`LIVEGRAPH_ADMIN_PASSWORD` in `.env`; unlocking stores a signed `HttpOnly`
cookie for twelve hours. `/api/admin/session` is the single exception, because
a page has to be able to ask whether it is logged in and whether a passphrase
was ever configured.

With no passphrase set the API refuses everything and the tab says so rather
than offering a login: a missing setting should be a locked door, not a silent
hole. Changing the passphrase invalidates outstanding sessions, because the
signing key is derived from it. The gate is on the router, not on individual
routes, so a route added later is protected by default — and a test enumerates
the admin surface from the app to keep that true.

**Credentials typed here override `.env`.** The page is the more recent
statement of intent, and edits that silently lose to an older file would be
worse than no edits at all. Each field says where its value came from — `set
here`, `from .env`, or `not set` — so an override is visible rather than
inferred. Clearing a field hands it back to `.env`.

The mobile number and the UCC are shown unmasked. They identify the account
rather than authorise it, and seeing them is how a typo is caught before Kotak
rejects it — a stray space in a phone number is invisible behind dots and fatal
at login, which is why pasted spacing is now stripped from both the number and
the base32 secret.

Values are written to `LIVEGRAPH_STATE_DIR` as `credentials.json`, mode 0600,
replaced atomically. In the container that path is a named volume, so what you
type survives `up --build`; from source it is `.livegraph/`, which is
git-ignored. Values are never returned by any endpoint and never logged — only
field names are.

**The MPIN is never stored.** Together with a code it is the whole account, so
keeping it on disk beside the secret that generates codes would put both halves
in one file. It is typed at each login instead, and a store written by an
earlier version has it deleted on the next read rather than merely ignored.
`.env` may still carry one for a deployment that logs in unattended.

**The daily login takes a typed code.** Kotak's API wants the six digits, not
the secret, and the secret is only how the app logs itself back in unattended.
With no usable secret stored, the tab shows a code box; with one, it derives
the code and the box disappears. A secret that is stored but cannot produce a
code is labelled as such, because it passes every presence check and would
otherwise read as correctly configured while the login it exists for fails.

A successful login starts the feed when none is running. That is safe precisely
because there is nothing to tear down: the app came up unconfigured, so no
socket and no prices exist yet. A feed that is already live is left alone —
replacing a running socket in place is a separate concern from starting one —
and so is an injected test feed.

Saving a credential does not rebuild anything. Log in afterwards, which does.

Model credentials are the exception: this app does not take them. Those logins
are OAuth flows that CLIProxyAPI owns and drives from its own control panel, so
the Admin tab reports whether the proxy answers and links out to it.

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

## There is no synthetic feed

Prices come from Kotak or they do not come at all. An invented price on a
screen built to be acted on is worse than an empty screen, so without working
credentials the app starts, serves the graph and the admin page, and shows no
prices. `FeedStatus.mode` says which state it is in:

| mode | meaning |
|---|---|
| `live` | streaming from Kotak Neo |
| `unconfigured` | credentials missing; the detail names which |
| `error` | credentials present, login failed; the detail carries the reason |
| `injected` | a feed was supplied by the caller, which only tests do |

The test suite supplies its own deterministic feed from `tests/fake_feed.py`.
It lives there rather than in the application on purpose: a synthetic feed the
product can start with by accident is exactly the failure this avoids.

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

Working: `graph`, `news`, `scratchpad`, `scan`, `agent`, `api` and the UI.

Unverified: the live Kotak path. Symbol mapping, tick normalisation and
nearest-expiry selection are tested; the TOTP login and socket subscribe are
not, because they need real credentials and an open market.
