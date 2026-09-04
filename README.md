# Stock Market Agentic Platform

Live NSE F&O prices from Kotak Neo, overlaid on a curated relationship graph of
the Nifty 500, with an agentic layer that runs on your existing Claude Code and
Codex subscriptions through CLIProxyAPI.

The application lives in [`apps/live-graph`](apps/live-graph); its README covers
setup, credentials and architecture in full.

## Quick start

```bash
cd apps/live-graph
docker compose up --build
```

Then open http://localhost:8000. Without Kotak credentials the app starts on a
simulated feed and says so, in an amber badge, on every screen.

From source instead:

```bash
make install
make run
```

## What it does

- **Scan** — the largest movers each way in the F&O tier, each carrying a
  verdict computed from peer and sector arithmetic plus typed graph edges:
  unexplained, conflicted, stock-specific or sector-wide. Drill from a mover
  into the stock, then into its peer group, its sector, or its graph drivers.
- **Graph** — 545 nodes and 3,003 typed edges, coloured by the live move.
- **Scratchpad** — describe a strategy in English; a model writes it and it runs
  in a WASM sandbox against a live snapshot, returning tables and charts.
- **Analyst** — ask questions; answers come from graph and price tools, never
  from memory.
- **Admin** — the Kotak session, which expires daily.

## Shape

One image, one container, one port. FastAPI serves the API, the tick WebSocket
and the exported UI, and hosts the strategy sandbox in-process as a Pyodide
(WASM) runtime, so nothing mounts the Docker socket and no sibling containers
are started.

Directory | Contents
---|---
`apps/live-graph` | The application: backend, UI, tests, Dockerfile
`tasks`, `design_specs`, `issues` | Planning history from the earlier desktop platform

## History

This repository previously held an Electron desktop shell and a separate Python
background service. Both were removed in favour of the single application in
`apps/live-graph`. The planning documents are kept for context.
