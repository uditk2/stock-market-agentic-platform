# Blueprint - Stock Market Agentic Platform (Canonical v1.2)

## Problem Statement
Build an auditable, modular NSE F&O futures recommendation desktop platform that keeps ingesting data in the background, supports interchangeable LLM agents, pluggable news feeds, and strategy module evolution without rewriting the core system.

## Constraints and Assumptions
- Kotak Neo is the canonical market data source in v1.
- Free-text strategy input must always be accepted.
- No rollover in v1.
- Recommendation-only scope (no broker execution automation in v1).
- Desktop-first runtime: core services must continue when UI is closed.
- Mandatory first-run wizard includes AI CLI setup validation.
- Release mode A (personal/internal unsigned-first) is locked for v1.

## Design Alternatives Considered
1. Monolith (UI + data + scheduling in one process): rejected due to low modularity and restart fragility.
2. UI-only scheduler (jobs run only while app open): rejected due to explicit requirement for background collection.
3. Service-first architecture with pluggable adapters and desktop control plane: chosen.

## Chosen Architecture
- Desktop Control Plane (`apps/desktop`): Electron shell + setup wizard + terminal + scheduler/job health UI.
- Background Service (`apps/service`): Python FastAPI + scheduler + ingestion + plugin registries.
- Shared Contracts (`packages/contracts`): JSON schema + typed DTOs for IPC/API stability.
- Plugin Interfaces:
  - `LLMAdapter` with `codex` and `claude` adapters behind same interface.
  - `NewsProvider` registry (NewsAPI, RSS, future sources).
  - `StrategyModule` registry for replaceable/updateable strategy logic.
- Packaging:
  - PyInstaller for service binaries.
  - electron-builder for desktop installers.
  - GitHub Actions matrix to build macOS/Windows/Linux artifacts.

## Interfaces / Modules
### Service modules
- `core/config`
- `core/logging`
- `core/interfaces` (`LLMAdapter`, `NewsProvider`, `StrategyModule`)
- `plugins/llm/*`
- `plugins/news/*`
- `plugins/strategy/*`
- `scheduler/*`
- `ingestion/*`
- `api/*`

### Desktop modules
- `main/*` (window lifecycle, service process manager, IPC)
- `preload/*` (safe IPC bridge)
- `renderer/*` (wizard, terminal view, scheduler view)

## Delivery Plan
- Phase 1 (this run): foundation code scaffolding + modular plugin contracts + background scheduler service + desktop shell + CI packaging workflow.
- Phase 2: real data source integrations and signal engines.
- Phase 3: recommendation lifecycle, monitoring, backtest, supervised learning.

## Risks and Open Questions
### Risks
- External API limits and unstable schemas.
- Packaging complexity across three OS targets.
- AI CLI redistribution/auth flows may vary by provider version.

### Open Questions (queued for next user window)
- OQ1: Preferred GitHub repo visibility/name if creating a new remote is required.
- OQ2: Initial default RSS feed list to ship in v1.
- OQ3: Minimum supported OS versions per platform.

## Sprint 1 Acceptance Targets
- Monorepo scaffold with clear module boundaries.
- Background scheduler process runs independently of UI process lifecycle.
- Plugin registries allow swapping LLM/news/strategy implementations by config.
- GitHub Actions workflow exists for cross-platform packaging artifacts.
- Local docs explain build/release flow and extension points.

## Wave 2 Focus (Reassessed)
- W1: move runtime state to SQLite persistence
- W2: source/feed configuration management
- W3-W4: mandatory CLI wizard + embedded terminal
- W5: OS background service install templates
- W6: real connector baseline
- W7-W8: CI hardening + integration/ops tests
- W9: issue sync and tracking
