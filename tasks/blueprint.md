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
- Wizard flow now owns operator-facing background-service installation (no manual script usage required for baseline UX).
- Packaged desktop runtime should self-resolve bundled service binary path without manual `SMAP_SERVICE_BIN` setup.
- Mandatory wizard lock must remain enforceable while still providing understandable, non-broken opening-screen controls.

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
  - W5 runtime follow-up adds packaged service binary auto-resolution and wizard-triggered install orchestration.
  - W5 runtime follow-up status: complete.
  - W5 runtime follow-up adds deterministic service binary resolver for packaged one-click startup.
  - W5 runtime follow-up status: complete.

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

### Current Slice: Wizard Opening UX Stabilization
- Problem statement:
  - Opening-screen Broker Provider dropdown appears broken due to lock-state disabling and missing fallback UI states.
- Constraints:
  - Do not remove mandatory wizard gate.
  - Keep behavior deterministic in Electron and preview/browser mode.
- Design alternatives considered:
  1. Fully unlock the workspace before wizard completion: rejected (breaks mandatory enforcement).
  2. Keep full lock and only add text hints: rejected (control still feels broken).
  3. Keep lock but allow safe discovery controls + explicit fallback states: chosen.
- Chosen architecture:
  - Renderer lock manager keeps mutating controls disabled.
  - Provider dropdown/reload remain usable even when lock is active.
  - Provider loading path injects explicit empty/error option states.
- Interfaces/modules:
  - `apps/desktop/renderer/index.html`:
    - `setWorkspaceLocked`
    - `loadProviders`
    - `boot` provider error handling
- Delivery plan:
  - Implement lock allowlist + fallback options.
  - Run desktop and service test suites.
  - Push and watch CI to green.
- Risks/open questions:
  - User still expects full auto-install flow for missing CLIs; policy decision remains pending separately.

### Current Slice: Wizard CLI Install Assistant
- Problem statement:
  - Wizard currently reports missing CLIs but does not help the user install them.
- Constraints:
  - Must ask user subscription ownership and intended CLI target.
  - Must preserve explicit user intent before execution.
  - Must keep mandatory wizard pass gate unchanged.
- Design alternatives considered:
  1. Auto-install all missing CLIs immediately: rejected (too implicit, subscription mismatch risk).
  2. Manual external docs only: rejected (still poor wizard UX).
  3. Wizard-driven selection + validated install plan + terminal-assisted execution: chosen.
- Chosen architecture:
  - Main process module returns validated install plan per selected subscription + CLI + platform.
  - Preload bridge exposes install-plan API to renderer.
  - Renderer wizard adds subscription selector, install-target selector, and install action.
- Interfaces/modules:
  - `apps/desktop/main/wizard_cli_install.js`
  - `apps/desktop/main/main.js` IPC handler
  - `apps/desktop/preload/preload.js`
  - `apps/desktop/renderer/index.html`
- Delivery plan:
  - Build install-plan module + tests.
  - Wire IPC and renderer controls.
  - Run desktop + service tests.
  - Push and monitor installer CI matrix to green.
- Risks/open questions:
  - CLI package names/install channels can change upstream; commands should remain easy to update in one module.

### Current Slice: Wizard Reliability + Step-by-Step UX
- Problem statement:
  - Users can install CLI and still fail mandatory checks due stale probe commands and non-scoped requirements; provider list can be unavailable during early service warmup.
- Constraints:
  - Keep mandatory gate behavior.
  - Keep subscription-driven CLI expectations.
  - Keep provider API calls resilient to startup race.
- Design alternatives considered:
  1. Keep current checks and only change labels: rejected (does not fix functional failures).
  2. Remove auth probing entirely: rejected (too weak for Codex where status exists).
  3. Update probes + subscription scoping + provider retry + stepper UX: chosen.
- Chosen architecture:
  - `cli_checks` accepts required CLI scope and uses current-compatible auth candidate for Codex.
  - renderer passes subscription into checks request.
  - renderer adds provider-load retry helper and wizard `Next` state machine.
- Interfaces/modules:
  - `apps/desktop/main/cli_checks.js`
  - `apps/desktop/main/main.js` (`cli-checks` IPC payload support)
  - `apps/desktop/preload/preload.js`
  - `apps/desktop/renderer/index.html`
- Delivery plan:
  - Patch check engine and tests.
  - Patch renderer retry + stepper.
  - Run desktop/service tests.
  - Push and monitor CI green.
- Risks/open questions:
  - Claude authentication introspection remains CLI-version sensitive; subscription scoping limits false-blocking for non-subscribed paths.

### Current Slice: DMG-Only Artifact Delivery
- Problem statement:
  - User download flow needs only macOS DMG, but CI artifact bundles include extra file types not needed for manual install.
- Constraints:
  - Keep matrix builds for macOS/Windows/Linux.
  - Narrow upload payloads without changing installer generation behavior.
- Design alternatives considered:
  1. Keep one shared upload glob for all OSes: rejected (over-shares artifacts).
  2. Remove non-DMG outputs from electron-builder targets: rejected (changes build outputs globally).
  3. Keep builds unchanged, split artifact upload paths per OS: chosen.
- Chosen architecture:
  - Conditional upload steps in GitHub Actions keyed by `matrix.os`.
  - macOS artifact upload includes only `*.dmg`.
- Interfaces/modules:
  - `.github/workflows/build-installers.yml`
- Delivery plan:
  - Patch workflow upload steps by OS.
  - Validate workflow syntax and run CI.
  - Share macOS artifact path with user.
- Risks/open questions:
  - Removing update metadata from uploaded artifacts may be incompatible with future auto-update channel expectations.

### Current Slice: Unsigned macOS Install Recovery
- Problem statement:
  - Without notarization credentials, macOS may block launch with quarantine/Gatekeeper messaging.
- Constraints:
  - No Apple signing/notarization credentials.
  - User needs deterministic recovery instructions outside app UI.
- Design alternatives considered:
  1. Keep ad-hoc manual guidance in chat only: rejected (not reproducible/self-service).
  2. Revert to mixed artifact bundle with extra files: rejected (contradicts DMG-only delivery ask).
  3. Add explicit unblock helper script + README guidance: chosen.
- Chosen architecture:
  - Provide repo-shipped helper script:
    - `scripts/macos/unblock_unsigned_app.sh`
  - Document both curl one-liner and local script path in README.
- Interfaces/modules:
  - `scripts/macos/unblock_unsigned_app.sh`
  - `README.md`
- Delivery plan:
  - Add script and documentation.
  - Push and validate CI remains green.
  - Share procedure with user.
- Risks/open questions:
  - This remains a workaround until notarization credentials are available.

### Current Slice: Direct DMG Release Publishing
- Problem statement:
  - Users want a direct DMG download, but GitHub Actions artifacts are always ZIP-wrapped.
- Constraints:
  - Keep existing Build Installers workflow.
  - Publish from successful macOS build leg only.
- Design alternatives considered:
  1. Keep artifact-only distribution: rejected (still ZIP wrapper).
  2. Manual upload per release: rejected (non-deterministic and slow).
  3. CI-managed stable latest release tag with clobbered DMG asset: chosen.
- Chosen architecture:
  - In `build-installers.yml`, add macOS-only release publish step for push events on master/main.
  - Release tag: `smap-mac-latest`.
  - Asset name: `SMAP-Desktop-macOS-latest.dmg`.
- Interfaces/modules:
  - `.github/workflows/build-installers.yml`
  - `README.md`
- Delivery plan:
  - Patch workflow permissions + release publish step.
  - Push and verify release asset update.
  - Share direct release URL with user.
- Risks/open questions:
  - Release tag is mutable by design; audit trail should rely on commit SHA and workflow run links.

### Current Slice: Codex Detection + Provider Visibility Fix
- Problem statement:
  - Wizard reports Codex not installed on mac despite installation, and providers appear unavailable when service is installed but not running.
- Constraints:
  - Keep mandatory lock behavior.
  - Preserve secure command execution boundaries.
- Design alternatives considered:
  1. Disable lock checks until service/provider config complete: rejected (weakens mandatory gating).
  2. Add manual support text only: rejected (does not fix functional detection/startup path).
  3. Improve PATH-aware CLI probes + allow start/refresh while locked + one-time service auto-start retry: chosen.
- Chosen architecture:
  - `cli_checks` now builds augmented command PATH for GUI-launched app environments.
  - Renderer lock bypass allows `startServiceBtn` + `refreshServiceBtn`.
  - Provider retry flow attempts service start once via bridge before final failure.
- Interfaces/modules:
  - `apps/desktop/main/cli_checks.js`
  - `apps/desktop/main/cli_checks.test.js`
  - `apps/desktop/renderer/index.html`
- Delivery plan:
  - Patch detection and lock/retry behavior.
  - Run desktop tests.
  - Push and verify Build Installers CI.
- Risks/open questions:
- PATH fallback covers common install paths; edge-case custom install locations may still require manual PATH configuration.

### Current Slice: W13 User-Requested UX and Data Workflow
- Problem statement:
  - User cannot tell why recommendations/news are empty, broker configuration should be inside Settings, terminal should be hidden by default, and overall home UX needs polish.
- Constraints:
  - Implement and track as separate GitHub issues, completed sequentially.
  - Preserve existing service API contracts and terminal safety controls.
  - Keep onboarding flow stable while moving broker controls to Settings.
- Design alternatives considered:
  1. Single bulk UI rewrite in one change: rejected (high risk, poor traceability).
  2. Separate issues but implement out of order: rejected (conflicts with user ask).
  3. Sequential issue-by-issue delivery with tests and closures: chosen.
- Chosen architecture:
  - Issue #20: add diagnostics-driven data status + refresh/empty-state UX.
  - Issue #21: move broker configuration into Settings modal/offcanvas.
  - Issue #22: hide terminal by default; add explicit open/close control.
  - Issue #23: polish layout and action hierarchy after structural moves.
- Interfaces/modules:
  - `apps/desktop/renderer/index.html`
  - `apps/desktop/preload/preload.js` (only if new bridge hooks are needed)
  - `apps/desktop/main/main.js` (only if new IPC hooks are needed)
  - `issues/issue-023-news-data-visibility-and-refresh.md`
  - `issues/issue-024-broker-configuration-settings-menu.md`
  - `issues/issue-025-terminal-collapsed-by-default.md`
  - `issues/issue-026-ui-polish-pass.md`
- Delivery plan:
  1. Complete Issue #20 and close.
  2. Complete Issue #21 and close.
  3. Complete Issue #22 and close.
  4. Complete Issue #23 and close.
- Risks/open questions:
  - If user expects live external news without API keys, diagnostics must clearly explain missing provider credentials/keys.

## Risks and Open Questions
### Risks
- External API limits and unstable schemas.
- Packaging complexity across three OS targets.
- AI CLI redistribution/auth flows may vary by provider version.
- Connector observability payloads can drift if schema discipline is not maintained across future job types.
- Service manager behaviors differ by OS; scripts must stay user-scope-safe and idempotent.
- CI artifacts can become large if unpacked build trees are uploaded; artifact policy must stay installer-only.

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

### Current Slice: First-Open Progressive Onboarding
- Problem statement:
  - Users are confused by immediate full-screen lock behavior; installer/detection/broker steps are not obvious in sequence.
- Constraints:
  - Keep mandatory CLI checks.
  - Keep provider API contract unchanged.
  - Support both Codex and Claude install/detect paths.
- Design alternatives considered:
  1. Keep current lock and add more text: rejected (does not simplify flow).
  2. Move all setup into terminal panel: rejected (too technical for first-time onboarding).
  3. Add staged UI (`setup -> broker -> home`) with background install: chosen.
- Chosen architecture:
  - Renderer onboarding state machine with stage-based visibility.
  - Main-process IPC for background CLI install execution.
  - Provider save action transitions stage to home.
- Interfaces/modules:
  - `apps/desktop/renderer/index.html`
  - `apps/desktop/main/wizard_cli_install.js`
  - `apps/desktop/main/main.js`
  - `apps/desktop/preload/preload.js`
- Delivery plan:
  - Add staged rendering and Next behavior.
  - Add background install IPC + tests.
  - Validate desktop test suite and CI.
- Risks/open questions:
  - Global npm installs may fail in user environments without proper permissions/PATH; wizard must show actionable failure text.

### Current Slice: Provider URL Undefined Port Hotfix
- Problem statement:
  - Provider fetch fails with URL parse error due to `127.0.0.1:undefined` base URL.
- Constraints:
  - Preserve existing service start flow and onboarding UX.
- Design alternatives considered:
  1. Renderer-only fallback: partially mitigates but hides launch metadata bug.
  2. Main-only port propagation: fixes source but lacks UI defense.
  3. Apply both propagation + UI fallback: chosen.
- Chosen architecture:
  - `service_runtime` guarantees numeric port in all launch modes.
  - Renderer validates launch metadata and falls back to `http://127.0.0.1:18787`.
- Interfaces/modules:
  - `apps/desktop/main/service_runtime.js`
  - `apps/desktop/main/service_runtime.test.js`
  - `apps/desktop/renderer/index.html`
- Delivery plan:
  - Patch, test, push, and publish new installer build link.
- Risks/open questions:
  - User environments with non-default custom ports still rely on valid launch metadata from main process.

### Current Slice: Launchd Running-State Reliability Hotfix
- Problem statement:
  - macOS wizard install can finish with launchd `installed=true` but `running=false`, preventing provider availability.
- Constraints:
  - Keep user-scope LaunchAgent model.
  - Keep behavior compatible with launchctl variants.
- Design alternatives considered:
  1. Keep load/unload and only add UI messaging: rejected (does not enforce startup).
  2. Force app-local service process only: rejected (bypasses background-service contract).
  3. Use bootout/bootstrap + kickstart and verify running with retries: chosen.
- Chosen architecture:
  - `background_service_manager` darwin install path runs `bootout`, `bootstrap` (or fallback), then `kickstart -k`.
  - Install returns failure if running state is not observed shortly after install.
- Interfaces/modules:
  - `apps/desktop/main/background_service_manager.js`
  - `apps/desktop/main/background_service_manager.test.js`
- Delivery plan:
  - Patch install order and status parser.
  - Add darwin install/status tests.
  - Ship patched desktop build.
- Risks/open questions:
  - If service binary crashes instantly, launchd can still leave non-running state; logs remain required for root-cause beyond install sequencing.

### Current Slice: Cross-Platform Service Running-State Parity
- Problem statement:
  - Only macOS had install-time running verification; Linux/Windows could report success while non-running.
- Constraints:
  - Keep existing per-OS install semantics.
  - Keep retry window bounded to avoid long UI stalls.
- Design alternatives considered:
  1. Keep platform-specific checks only: rejected (behavior drift/confusing UX).
  2. Require immediate running with no retries: rejected (race-prone startup).
  3. Shared post-install running verifier for all supported platforms: chosen.
- Chosen architecture:
  - Introduce shared `waitForRunningStatus` helper in desktop service manager.
  - Fail install when final status remains non-running.
- Interfaces/modules:
  - `apps/desktop/main/background_service_manager.js`
  - `apps/desktop/main/background_service_manager.test.js`
- Delivery plan:
  - Patch shared verifier.
  - Add linux fail and windows delayed-run tests.
  - Validate linux host install path.
- Risks/open questions:
  - Provider endpoint verification on this Linux host is blocked by current packaged service binary import failure, separate from service-manager sequencing.

### Current Slice: Packaged Service Import Runtime Recovery
- Problem statement:
  - Packaged service binary crashed due missing `smap_service` import resolution.
- Constraints:
  - Keep packaged startup path simple and deterministic.
  - Avoid broad packaging changes outside import inclusion.
- Design alternatives considered:
  1. Spec-only hidden import additions: partial, still relies on string indirection.
  2. Entry-point direct import + spec hidden import reinforcement: chosen.
  3. Bypass packaged binary and force source runtime: rejected for installer path.
- Chosen architecture:
  - Entry point imports `app` directly and passes object to `uvicorn.run`.
  - PyInstaller spec includes `smap_service.main` in hidden imports.
- Interfaces/modules:
  - `apps/service/src/smap_service/entrypoint.py`
  - `apps/service/smap_service.spec`
- Delivery plan:
  - Patch import path and spec.
  - Rebuild packaged binary.
  - Validate provider endpoint from packaged runtime.
- Risks/open questions:
  - Future dynamically imported modules may still require explicit hidden imports if introduced.

### Current Slice: W14 Runtime Usability and Kotak Verification
- Problem statement:
  - Users report Refresh/Search controls appear inactive, records remain zero without clear causes, Kotak credential validity is opaque, and Backtesting/ML options are not visible.
- Constraints:
  - Keep current desktop/service architecture and avoid order-trading side effects.
  - Use official Kotak Neo primary sources for API alignment.
  - Keep fixes incremental and issue-scoped.
- Design alternatives considered:
  1. Only add UI messaging without connector/API changes: rejected (does not address ingestion/auth correctness).
  2. Full backtesting/ML engine implementation immediately: rejected (too broad for support hotfix window).
  3. Deliver visibility/verification + API alignment now, with dedicated follow-up issues for full engines: chosen.
- Chosen architecture:
  - Renderer: explicit action feedback for search/refresh, richer diagnostics rendering, and visible workspace mode entry points.
  - Service: Kotak connector aligned to official quote/scrip-master patterns and diagnostics credential verification payload.
  - Tracking: separate issue IDs for each user-reported problem and sequential resolution.
- Interfaces/modules:
  - `apps/desktop/renderer/index.html`
  - `apps/service/src/smap_service/plugins/market/kotak_client.py`
  - `apps/service/src/smap_service/api/routes.py`
  - GitHub issues `#29` to `#33`
- Delivery plan:
  - Issue #29: Refresh/Search interaction feedback.
  - Issue #30: Kotak API correctness + credential verification.
  - Issue #31: records=0 cause visibility.
  - Issue #32: Backtesting visibility entry point.
  - Issue #33: ML recommendations visibility entry point.
- Risks/open questions:
  - User-provided Kotak credential field currently named `access_token`; if they are using a different key type, additional schema normalization may be required.
  - Quote ingestion still depends on symbol-token resolution from scrip master data availability.

### Current Slice: W15 Functional-Correctness Recovery and Revalidation
- Problem statement:
  - User-reported functional dissatisfaction indicates substantial behavior gaps relative to design FR1-FR15 despite prior issue closures.
  - Runtime evidence shows at least one hard defect (`/connectors/diagnostics` crash), and Kotak token validation is not enforced pre-save.
- Constraints and assumptions:
  - Functional correctness takes precedence over UI polish.
  - Broker-side verification must stay read-only (no trading/order APIs).
  - Existing architecture (Electron renderer + FastAPI service + SQLite) remains in place.
- Design alternatives considered:
  1. Patch only visible UI controls: rejected (does not guarantee FR correctness or backend stability).
  2. Full greenfield rewrite of service/recommendation stack: rejected for this pass due risk and delivery time.
  3. Incremental correctness recovery with traceability-first execution: chosen.
- Chosen architecture:
  - Add FR traceability matrix and issue mapping as the source of truth for this pass.
  - Stabilize core service APIs first (diagnostics and credential flow).
  - Enforce provider verification before credential persistence for Kotak.
  - Re-test UI actions against stable APIs and expose explicit failure causes.
- Interfaces/modules:
  - `apps/service/src/smap_service/api/routes.py`
  - `apps/service/src/smap_service/app_runtime.py`
  - `apps/service/src/smap_service/plugins/market/kotak_client.py`
  - `apps/service/tests/test_health_route.py`
  - `apps/service/tests/test_connector_observability_smoke.py`
  - `apps/desktop/renderer/index.html`
  - `issues/issue-039-fr-audit-and-functional-gap-recovery.md` (new)
- Delivery plan:
  - Phase 1: FR1-FR15 audit + closed-issue revalidation + defect inventory.
  - Phase 2: Core API correctness fixes (diagnostics stability + pre-save Kotak validation).
  - Phase 3: Workflow verification (refresh/search, connector diagnostics, recommendation visibility).
  - Phase 4: Re-run tests, update issues, and publish final gap report.
- Risks and open questions:
  - FR1-FR15 includes substantial algorithmic features not yet implemented; multiple follow-up slices are expected.
  - Live Kotak validation depends on external API availability/rate limiting.

### Current Slice: W15F FR1-FR4 Ingestion Persistence Foundations
- Problem statement:
  - FR1-FR4 require durable ingestion and broader symbol coverage, while current flow was largely transient.
- Constraints and assumptions:
  - Keep incremental scope limited to ingestion/persistence foundations.
  - Keep safe fallback to fixed symbols when dynamic discovery cannot run.
- Design alternatives considered:
  1. Keep transient in-memory ingestion only: rejected (no lookback continuity).
  2. Build full FR1-FR4 pipeline in one jump: rejected (too broad for a single correction slice).
  3. Add persistent ingestion primitives + dynamic symbol discovery hook: chosen.
- Chosen architecture:
  - Add `SQLiteMarketDataStore` with `market_bars` and `news_items` tables.
  - Wire scheduler jobs to persist market/news/announcement ingestion outputs.
  - Add Kotak scrip-master-driven symbol discovery method for stock futures.
- Interfaces/modules:
  - `apps/service/src/smap_service/db/market_data.py`
  - `apps/service/src/smap_service/scheduler/manager.py`
  - `apps/service/src/smap_service/ingestion/jobs.py`
  - `apps/service/src/smap_service/plugins/market/kotak_client.py`
- Delivery plan:
  - Implement schema/store.
  - Integrate scheduler persistence.
  - Add tests and run full service suite.
- Risks and open questions:
  - Dynamic symbol discovery still depends on upstream Kotak availability.
  - Full FR4 symbol/sector mapping quality remains a follow-up implementation track.

### Current Slice: W15G FR5-FR8 Signal Computation and Persistence
- Problem statement:
  - FR5-FR8 are currently unimplemented; no persisted signal model exists.
- Constraints and assumptions:
  - Keep initial signal model deterministic and testable.
  - Build on newly persisted market/news ingestion data.
- Design alternatives considered:
  1. Add only placeholder signal rows: rejected (not functionally meaningful).
  2. Full quantitative stack in one step: rejected (too broad/risky).
  3. Incremental deterministic signal engine + persistence schema: chosen.
- Chosen architecture:
  - New signal engine module computes S/R proxies, pattern flags, and fused score.
  - New `signals` table stores stable `signal_id` and feature payload.
  - Scheduler adds `compute_signals` job and records observability metadata.
- Interfaces/modules:
  - `apps/service/src/smap_service/core/signals.py` (new)
  - `apps/service/src/smap_service/db/market_data.py`
  - `apps/service/src/smap_service/scheduler/manager.py`
  - `apps/service/src/smap_service/api/routes.py` (diagnostics surface)
- Delivery plan:
  - Add schema + engine.
  - Wire scheduler job.
  - Add tests and validate service suite.
- Risks and open questions:
  - Score quality is baseline and requires iterative calibration with real market outcomes.

### Current Slice: W15H FR9-FR12 Strategy and Recommendation Contract
- Problem statement:
  - FR9-FR12 remain incomplete: no strategy artifact versioning, no full recommendation contract, and limited publish guardrails/linkage.
- Constraints and assumptions:
  - Keep API backward-compatible where practical.
  - Keep recommendation generation deterministic and auditable.
- Design alternatives considered:
  1. Continue static recommendation payloads: rejected.
  2. Full production recommendation engine in one pass: rejected (too broad).
  3. Add persistence + contract + baseline guardrails with signal linkage: chosen.
- Chosen architecture:
  - New strategy artifact persistence with free-text versioning.
  - New recommendation persistence model with FR10 fields.
  - Link table from recommendation to signal IDs.
  - Guardrail suppress-on-fail logic with stored suppress reason.
- Interfaces/modules:
  - `apps/service/src/smap_service/db/market_data.py`
  - `apps/service/src/smap_service/core/recommendations.py`
  - `apps/service/src/smap_service/api/routes.py`
  - `apps/service/src/smap_service/scheduler/manager.py` (job wiring)
- Delivery plan:
  - Add schema and persistence paths.
  - Add strategy/recommendation APIs.
  - Add generation + guardrails + tests.
- Risks and open questions:
  - Guardrail thresholds are baseline and may require calibration.

### Current Slice: W15I FR13-FR15 Recommendation Lifecycle and Labels
- Problem statement:
  - FR13-FR15 need lifecycle monitoring, close-trigger enforcement, and closure-label persistence, currently missing.
- Constraints and assumptions:
  - Use per-lot P&L approximation with current market bar close.
  - Keep lifecycle deterministic and auditable.
- Design alternatives considered:
  1. Manual closure only: rejected.
  2. Full production risk engine in one pass: rejected.
  3. Baseline lifecycle evaluator + close-trigger persistence: chosen.
- Chosen architecture:
  - Scheduler lifecycle job evaluates open recommendations.
  - Trigger engine applies profit/loss/cutoff closures.
  - Recommendations table stores closure metadata as labels.
- Interfaces/modules:
  - `apps/service/src/smap_service/core/recommendations.py`
  - `apps/service/src/smap_service/db/market_data.py`
  - `apps/service/src/smap_service/scheduler/manager.py`
  - `apps/service/src/smap_service/api/routes.py`
- Delivery plan:
  - Add closure fields and DB update path.
  - Add lifecycle evaluator and scheduler wiring.
  - Add tests for trigger behavior and label persistence.
- Risks and open questions:
  - Accurate expiry/cutoff semantics need full contract/calendar integration in later slices.

### Current Slice: W15J FR13-FR15 Lifecycle Precision (Lot Size + Expiry Cutoff)
- Problem statement:
  - W15I delivered baseline lifecycle behavior, but P&L still assumes `lot_size=1` and cutoff still uses generic 24h age.
- Constraints and assumptions:
  - Keep behavior deterministic and backward-compatible for records missing instrument metadata.
  - Keep fallback closure path available when expiry metadata is not yet discovered.
- Design alternatives considered:
  1. Keep static lot size and 24h cutoff: rejected (low correctness for F&O outcomes).
  2. Require full exchange calendar/contract master before any lifecycle run: rejected (blocks operations).
  3. Add progressive precision with persisted instrument specs and fallback path: chosen.
- Chosen architecture:
  - New instrument-spec persistence (`symbol`, `lot_size`, `expiry_date`, source metadata).
  - Kotak symbol-master parser extracts lot size/expiry hints and stores them via ingestion path.
  - Lifecycle evaluator computes realized P&L using symbol lot size when present.
  - Cutoff trigger checks expiry-day IST cutoff first; falls back to age-based rule when metadata is absent.
- Interfaces/modules:
  - `apps/service/src/smap_service/plugins/market/kotak_client.py`
  - `apps/service/src/smap_service/ingestion/jobs.py`
  - `apps/service/src/smap_service/db/market_data.py`
  - `apps/service/src/smap_service/core/recommendations.py`
  - `apps/service/tests/test_recommendations.py`
  - `apps/service/tests/test_connectors_baseline.py`
- Delivery plan:
  - Add instrument-spec schema + persistence API.
  - Extend Kotak parser and ingestion wiring.
  - Switch lifecycle P&L/cutoff logic to metadata-aware path with fallback.
  - Add focused tests and run service suite.
- Risks and open questions:
  - Kotak CSV schema may vary by account/feed; parser must remain tolerant and fallback-safe.

### Current Slice: W15K FR1-FR4 Completeness (Universe + Sector Mapping)
- Problem statement:
  - FR1-FR4 still lack full ingestion-universe guarantees and richer symbol/sector mapping quality in the persisted market metadata.
- Constraints and assumptions:
  - Keep ingestion deterministic when Kotak dynamic discovery is partially available or unavailable.
  - Avoid regressions in existing ingestion job contracts.
- Design alternatives considered:
  1. Keep dynamic-only discovery from connector: rejected (coverage can shrink during upstream/API instability).
  2. Keep static fallback-only list: rejected (misses discoverable futures breadth).
  3. Merge dynamic discovery with curated baseline and persist inferred sector metadata: chosen.
- Chosen architecture:
  - Add shared curated futures catalog with broad baseline stock-futures set and sector inference helpers.
  - Merge symbol universe as: `dynamic ∪ curated`, with normalized uppercase deterministic ordering.
  - Extend instrument spec persistence to include `sector`.
  - Enrich ingestion attribution with symbol-count quality metadata.
- Interfaces/modules:
  - `apps/service/src/smap_service/core/symbol_catalog.py` (new)
  - `apps/service/src/smap_service/ingestion/jobs.py`
  - `apps/service/src/smap_service/db/market_data.py`
  - `apps/service/src/smap_service/core/recommendations.py` (spec read compatibility)
  - `apps/service/tests/test_market_data_store.py`
  - `apps/service/tests/test_connectors_baseline.py`
- Delivery plan:
  - Add catalog + inference helpers.
  - Add merged-universe resolver behavior.
  - Add sector persistence/migration support.
  - Add tests and run service suite.
- Risks and open questions:
  - Sector inference is baseline taxonomy and may need periodic refinement as F&O universe evolves.

### Current Slice: W15L FR5-FR8 Signal Calibration
- Problem statement:
  - FR5-FR8 baseline signal engine is operational but fused scoring remains coarse and under-calibrated for trend/volatility context.
- Constraints and assumptions:
  - Preserve deterministic output and stable signal IDs for a fixed market snapshot.
  - Keep implementation explainable (no black-box model in this slice).
- Design alternatives considered:
  1. Keep current binary-flag scoring: rejected (insufficient ranking quality).
  2. Replace with ML model now: rejected (premature complexity for this recovery phase).
  3. Add deterministic trend/volatility features with calibrated weighting: chosen.
- Chosen architecture:
  - Extend feature extraction with:
    - normalized trend strength from rolling closes,
    - volatility regime from range/ATR-like proxy.
  - Rework fused-score function to combine existing flags and new calibration features.
  - Persist new features in `features_json`.
- Interfaces/modules:
  - `apps/service/src/smap_service/core/signals.py`
  - `apps/service/tests/test_signals.py`
- Delivery plan:
  - Add derived metrics + calibrated scoring.
  - Update tests for feature presence and score bounds/determinism.
  - Validate full service suite.
- Risks and open questions:
  - Weight choices are still heuristic and require future outcome-based tuning.

### Current Slice: W15M FR9-FR12 Recommendation Publish Calibration
- Problem statement:
  - FR9-FR12 recommendation contract exists, but publish logic is still lenient and can pass weak risk-reward setups.
- Constraints and assumptions:
  - Preserve existing API contract fields.
  - Keep suppression reasons explicit for auditability.
- Design alternatives considered:
  1. Keep current minimal guardrails: rejected.
  2. Introduce full portfolio optimizer: rejected (out of scope for recovery phase).
  3. Add calibrated publish thresholds and improved target construction: chosen.
- Chosen architecture:
  - Improve target-distance construction to increase baseline reward relative to risk.
  - Extend guardrails with minimum risk-reward and spread sanity checks.
  - Apply volatility-aware confidence thresholding using signal features where available.
- Interfaces/modules:
  - `apps/service/src/smap_service/core/recommendations.py`
  - `apps/service/tests/test_recommendations.py`
- Delivery plan:
  - Patch recommendation generation + guardrail logic.
  - Add tests for suppression reasons and publish pass path.
  - Validate full service suite.
- Risks and open questions:
  - Thresholds remain heuristic; outcome-driven calibration is a follow-up track.

### Current Slice: W15N FR13-FR15 Calendar Precision Fallback
- Problem statement:
  - Lifecycle cutoff uses explicit expiry metadata when present, but fallback behavior still lacks exchange-calendar semantics when metadata is missing.
- Constraints and assumptions:
  - Preserve explicit `expiry_date` precedence.
  - Keep deterministic behavior without introducing external calendar service dependency.
- Design alternatives considered:
  1. Keep elapsed-time fallback only: rejected (low calendar realism).
  2. Integrate full exchange calendar provider now: rejected (scope/time overhead for this slice).
  3. Add deterministic monthly-expiry fallback inference (last Thursday, IST): chosen.
- Chosen architecture:
  - Add helper to infer monthly futures cutoff from recommendation creation timestamp.
  - Apply precedence:
    - explicit expiry cutoff,
    - inferred monthly expiry cutoff,
    - final elapsed-time fallback for malformed timestamps.
- Interfaces/modules:
  - `apps/service/src/smap_service/core/recommendations.py`
  - `apps/service/tests/test_recommendations.py`
- Delivery plan:
  - Implement inference helper and cutoff precedence logic.
  - Add tests for elapsed/non-elapsed inferred cutoff behavior.
  - Validate full service suite.
- Risks and open questions:
  - Last-Thursday fallback is a practical proxy; holiday-adjusted expiry handling remains a future enhancement.

### Current Slice: W15O FR1-FR4 Completeness Closure (Priority #1)
- Problem statement:
  - FR1-FR4 has major foundations and refinements, but completion closure still needs explicit minimum-universe guarantees and richer coverage attribution.
- Constraints and assumptions:
  - Keep deterministic merged universe behavior.
  - Maintain compatibility with existing ingestion/scheduler interfaces.
- Design alternatives considered:
  1. Leave current merged-universe logic unchanged: rejected (closure criteria remains implicit).
  2. Dynamic-discovery hard dependency: rejected (fragile during upstream outages).
  3. Add explicit required baseline futures + coverage attribution metrics: chosen.
- Chosen architecture:
  - Extend curated baseline set with required macro/index futures.
  - Enhance ingestion attribution payload with dynamic/curated/merged counts.
  - Keep deduplicated sorted merged output.
- Interfaces/modules:
  - `apps/service/src/smap_service/core/symbol_catalog.py`
  - `apps/service/src/smap_service/ingestion/jobs.py`
  - `apps/service/tests/test_symbol_catalog.py`
  - `apps/service/tests/test_connectors_baseline.py`
- Delivery plan:
  - Patch baseline and attribution.
  - Add targeted tests for baseline guarantee and attribution shape.
  - Validate full service suite.
- Risks and open questions:
  - Universe breadth still benefits from future exchange-driven contract catalog ingestion.

### Current Slice: W15P FR5-FR8 Closure (Priority #2)
- Problem statement:
  - Signal engine and calibration are implemented, but issue #41 still lacks explicit API exposure closure for downstream consumers.
- Constraints and assumptions:
  - Reuse persisted signal rows; avoid introducing new storage schema.
  - Keep route lightweight and deterministic.
- Design alternatives considered:
  1. Keep signals internal only: rejected.
  2. Add heavy analytics endpoint now: rejected (scope creep).
  3. Add focused `/signals/recent` route with persisted contract fields: chosen.
- Chosen architecture:
  - API route fetches `list_recent_signals(limit)` from store.
  - Route returns stable list payload for UI/integration consumers.
- Interfaces/modules:
  - `apps/service/src/smap_service/api/routes.py`
  - `apps/service/tests/test_health_route.py`
- Delivery plan:
  - Add route and response payload.
  - Add route tests.
  - Validate full service suite and close #41.
- Risks and open questions:
  - Outcome-based ranking quality tuning remains separate from route exposure completion.

### Current Slice: W15Q FR9-FR12 Closure (Priority #3)
- Problem statement:
  - Recommendation generation and publish guardrails are calibrated, but issue #42 still lacks explicit quality-metrics exposure for operational monitoring.
- Constraints and assumptions:
  - Reuse persisted recommendation rows; avoid schema changes in closure pass.
  - Keep metrics route deterministic and lightweight.
- Design alternatives considered:
  1. Keep diagnostics implicit only: rejected.
  2. Add full analytics subsystem now: rejected (scope creep).
  3. Add focused recommendation-metrics route with suppression distribution: chosen.
- Chosen architecture:
  - New route computes aggregate counts by status and suppression reason from persisted recommendations.
  - Route supports quick quality monitoring for publish/suppress calibration outcomes.
- Interfaces/modules:
  - `apps/service/src/smap_service/core/recommendations.py`
  - `apps/service/src/smap_service/api/routes.py`
  - `apps/service/tests/test_health_route.py`
- Delivery plan:
  - Add metrics computation helper.
  - Add route and tests.
  - Validate full service suite and close #42.
- Risks and open questions:
  - Outcome-driven calibration still needs live/historical performance feedback loops outside this closure slice.
