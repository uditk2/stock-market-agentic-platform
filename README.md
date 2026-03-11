# Stock Market Agentic Platform

Modular desktop platform scaffold for NSE F&O signal/recommendation workflows.

## Monorepo Layout
- `apps/service`: Python background service (scheduler + ingestion + APIs + plugin registries)
- `apps/desktop`: Electron desktop shell (wizard + terminal + service control)
- `packages/contracts`: shared contracts used by service and desktop
- `.github/workflows`: CI build and packaging pipeline

## Quick Start

### Service
```bash
cd apps/service
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn smap_service.main:app --reload --port 8787
```

### Desktop
```bash
cd apps/desktop
npm install
npm run dev
```

## Current Sprint Status
Sprint 1 scaffolding implemented with pluggable interfaces:
- `LLMAdapter`
- `NewsProvider`
- `StrategyModule`

Background scheduler runs inside service process and is designed to keep ingestion jobs independent from the UI lifecycle.
