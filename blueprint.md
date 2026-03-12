# Blueprint - Stock Market Agentic Platform (Canonical v1.3)

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
- W1 runtime state persistence uses SQLite in per-user app data path.
- W1 retention policy is unlimited until a later explicit cap decision.
- W2 onboarding choice `1C` is accepted.
- W2 broker feed choice must support Kotak Neo, Upstox, and Kite.
- W2 keeps news source input hidden from end users (defaults only).
- Daily operating UX is recommendations-first with searchable F&O symbols.
- W2 credential storage is encrypted-at-rest in local SQLite.
- W2 home scope is recommendations + search only (watchlist deferred).
- W2 default recommendation order is confidence descending.
- W2 interface uses Bootstrap 5 component patterns for consistency and operator usability.
- W5 background-service installation defaults to user scope (`systemd --user`, `LaunchAgent`, user Task Scheduler job).
- W5 templates accept configurable service command/arguments to support packaged and source runtime variants.

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
- W2 UX Composition:
  - Setup: broker choice selector + credential capture form (provider-specific fields).
  - Daily home: recommendations list + instrument search bar.
  - Recommendation drill-down: tabbed details for news impact, technicals, and strategy rationale.

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
- `db/provider_credentials` (encrypted credential storage + provider selection)
- `core/recommendations` (recommendation list/detail payload composition)
- `core/retry` (shared retry/backoff wrapper for connector calls)
- `plugins/market/*` (market connector adapters)

### Desktop modules
- `main/*` (window lifecycle, service process manager, IPC)
- `preload/*` (safe IPC bridge)
- `renderer/*` (wizard, terminal view, scheduler view, recommendation workspace)
  - Uses Bootstrap cards/nav-tabs/forms/toasts and iconography for standardized UX affordances.
  - W4 adds a PTY-backed terminal panel with profile-gated command execution and explicit advanced mode.
  - W5 adds service-install template renderer + OS helper scripts for background runtime setup.

## Delivery Plan
- Phase 1 (this run): foundation code scaffolding + modular plugin contracts + background scheduler service + desktop shell + CI packaging workflow.
- Phase 2: W2 UX/provider management implementation, then real data source integrations and signal engines.
  - Slice 2A complete: W2 provider UX + credential persistence + recommendation workspace.
  - Slice 2B complete: W6 connector baseline (Kotak/NewsAPI/RSS/NSE adapters + diagnostics + attribution observability).
- Phase 2.5:
  - W4 embedded terminal runtime complete (PTY session manager, profile gating, advanced mode toggle, renderer terminal panel).
  - W3 wizard enforcement complete (mandatory CLI install/version/auth gating before workspace unlock).
- Phase 2.75:
  - W5 background service installation layer:
    - template-driven descriptor generation (Linux/macOS/Windows)
    - install/uninstall helper scripts
    - test coverage for renderer correctness
  - Status: complete.
- Phase 3: recommendation lifecycle, monitoring, backtest, supervised learning.

## Risks and Open Questions
### Risks
- External API limits and unstable schemas.
- Packaging complexity across three OS targets.
- AI CLI redistribution/auth flows may vary by provider version.
- Connector observability payloads can drift if schema discipline is not maintained across future job types.
- Service manager behaviors differ by OS; scripts must stay user-scope-safe and idempotent.

### Open Questions (queued for next user window)
- OQ1: Preferred GitHub repo visibility/name if creating a new remote is required.
- OQ2: Minimum supported OS versions per platform.

## Sprint 1 Acceptance Targets
- Monorepo scaffold with clear module boundaries.
- Background scheduler process runs independently of UI process lifecycle.
- Plugin registries allow swapping LLM/news/strategy implementations by config.
- GitHub Actions workflow exists for cross-platform packaging artifacts.
- Local docs explain build/release flow and extension points.

## Wave 2 Focus (Reassessed)
- W1: move runtime state to SQLite persistence
- W2: broker/feed UX + credential capture + recommendations-first workspace
- W3-W4: mandatory CLI wizard + embedded terminal
- W5: OS background service install templates
- W6: real connector baseline
- W7-W8: CI hardening + integration/ops tests
- W9: issue sync and tracking
