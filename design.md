# Stock Market Agentic Platform
## Design Document
Version 1.3 | March 2026

## 1. Problem Statement
Indian retail traders in NSE F&O need a modular recommendation platform with continuous background ingestion, transparent signal lineage, and extensible AI/strategy/news components.

## 2. Scope
In scope:
- NSE F&O stock futures (monthly contracts)
- Background data collection when UI is closed
- Pluggable news ingestion (APIs + RSS)
- Interchangeable LLM adapters
- Modular strategy modules
- Cross-platform desktop installers via CI

Out of scope:
- Broker execution automation
- RL optimization in v1

## 3. Functional Requirements (unchanged canonical)
- FR1-FR15 remain as defined in canonical v1.1 planning.

## 4. Sprint 1 Technical Design
### 4.1 Monorepo Layout
- `apps/desktop`: Electron desktop app
- `apps/service`: Python background service
- `packages/contracts`: shared contracts/schemas
- `.github/workflows`: build and packaging pipelines

### 4.2 Modularity Boundaries
- LLM adapters implement `LLMAdapter` interface and are selected by config.
- News sources implement `NewsProvider` interface and are registered dynamically.
- Strategies implement `StrategyModule` interface and are loaded by registry.
- Scheduler jobs call provider registries, not concrete providers.

### 4.3 Background Execution Model
- `apps/service` runs as independent long-running process.
- Desktop app starts/stops/monitors service but scheduler continues per configured mode.
- Jobs are idempotent and write run history for catch-up behavior.

### 4.4 Installer/Release Model
- Service packaged per OS with PyInstaller.
- Desktop bundled with electron-builder including service binary.
- GitHub Actions matrix generates platform installers/artifacts.
- Release mode A: unsigned-first artifacts for personal/internal use.

## 5. Open Questions to Defer to Morning Review
- Repository naming/visibility preference if remote creation diverges.
- Initial default RSS source set.
- Production signing timeline (post v1 unsigned-first).

## 6. Wave 2 Reassessment Notes
- The S1-S8 scaffold phase is complete.
- Next execution order is W1->W2->W3->W6->W4->W5->W8->W7->W9.
- Priority remains modular extension points and background-runtime reliability.
- W1 decisions locked:
  - SQLite DB location: per-user app data directory (Option A)
  - Job history retention: unlimited (no timeline cap for now)

## 7. W2 UX and Provider Decisions (User-Driven, March 2026)
Locked decisions:
- Onboarding flow uses choice `1C` (user-confirmed).
- Feed management must ask user to choose broker provider from:
  - Kotak Neo
  - Upstox
  - Kite
- UI must collect provider-specific credentials and store them in SQLite.
- News input configuration is not exposed to user in W2 (system-managed defaults only).
- Main daily page is recommendations-first.
- Recommendation detail must open on click with tabbed rationale:
  - Influential news
  - Technical indicators
  - Strategy explanation
- Main daily page must include search for specific NSE F&O instruments.

Final W2 locks:
- Credential storage in SQLite: `B` encrypted-at-rest.
- Daily page scope: `2A` recommendations + search only in W2.
- Recommendation ordering default: `3A` confidence score (descending).
- Interface polish direction: industry-standard UX patterns with established component libraries.

W2 UX polish delivered:
- Bootstrap 5-based design system for layout, forms, list patterns, tabs, and feedback toasts.
- Bootstrap Icons for consistent action/status affordances.
- Recommendations workflow improved with active list state, keyboard-search behavior, and clearer detail hierarchy.

## 8. W6 Connector Baseline (Slices 1-3, March 2026)
Implemented baseline connector layer with retry/backoff and normalized output contracts:
- Kotak market feed client (credential-aware, graceful fallback when missing token)
- NewsAPI adapter (API-key driven fetch + normalization)
- RSS poller/parser (feed list + retry + XML normalization)
- NSE announcements adapter (JSON endpoint adapter + normalization)

Scheduler wiring updates:
- Market ingestion now uses connector client output instead of pure scaffold ticks.
- Health metadata now includes active market connector identifier.

Slice 2 hardening:
- Provider-specific required-field validation for Kotak/Upstox/Kite credentials.
- Structured API error payloads for missing credential fields.
- Connector diagnostics route for market/news readiness snapshots.

Slice 3 observability and attribution:
- Job history rows now persist connector attribution, execution duration, and run context metadata.
- `/jobs/history` now exposes connector-level run attribution for operational traceability.
- `/connectors/diagnostics` now includes latest per-job run snapshots and scheduler failure counters.
- `/connectors/observability` added for recent run feed + aggregate summary.
- Integration smoke coverage added for scheduler-path run attribution and observability payload shape.

## 9. W4 Embedded Terminal Runtime (March 2026)
Objective:
- Provide an in-app operator terminal without collapsing security boundaries.

Design constraints:
- Renderer cannot execute shell directly; command execution stays in main process.
- Terminal must support safe command profiles by default.
- Advanced mode must be explicit and user-triggered.

Chosen approach:
- Add a main-process PTY session manager that owns lifecycle for one active terminal session.
- Expose narrow IPC contract through preload:
  - start session (profile + advanced mode flag)
  - write input
  - resize terminal
  - stop session
  - subscribe to output and exit events
- Renderer adds a terminal panel with:
  - profile selector (safe defaults)
  - advanced-mode toggle
  - output console viewport
  - input prompt and send action

Safe profiles (W4 baseline):
- `ops_status`: readonly diagnostics (`pwd`, `ls`, `git status`, service health curls)
- `service_logs`: journalctl/service-tail helpers
- `repo_dev`: scoped repo commands (no destructive git operations)

Guardrails:
- Advanced mode is opt-in and visually explicit.
- Profile mode validates command allowlist before execution.
- Session teardown on app exit/window close.

Delivered implementation:
- Electron main-process PTY session manager added with IPC handlers for start/write/resize/stop.
- Safe command profiles implemented (`ops_status`, `service_logs`, `repo_dev`) with metacharacter blocking.
- Explicit advanced-mode toggle added to permit unrestricted command entry when intentionally enabled.
- Preload bridge now exposes terminal APIs and output/exit subscriptions.
- Renderer now includes an embedded terminal panel with profile selection, mode toggle, output console, and command input.

## 10. W3 Mandatory AI CLI Wizard Enforcement (March 2026)
Objective:
- Block workspace usage until required AI CLIs are installed, version-detected, and authenticated.

Delivered implementation:
- Added main-process CLI check engine (`main/cli_checks.js`) with mandatory probes for:
  - install/availability (`--version`)
  - version extraction
  - auth/session checks (candidate commands per CLI)
- Added preload bridge method `cliChecks`.
- Added renderer setup wizard card with mandatory check execution and status rendering.
- Added workspace lock gating: all workspace controls remain disabled until wizard checks pass.
- Added unit tests for CLI check engine behavior.

## 11. W5 Background Service Installation Layer (March 2026)
Objective:
- Allow SMAP service runtime to stay active without the desktop UI, using native OS user-scoped service managers.

Design constraints:
- Keep baseline installs user-scoped (no mandatory system-wide admin requirement).
- Keep service command configurable for packaged binary vs source runtime.
- Keep templates deterministic and versionable in-repo.

Design alternatives considered:
- Pure shell-generated service descriptors: fast but duplicated logic across OS scripts.
- Template + renderer utility: chosen for consistency and lower drift risk.

Chosen approach:
- Add reusable service descriptor templates for:
  - Linux systemd user unit
  - macOS launchd LaunchAgent plist
  - Windows Task Scheduler XML
- Add a desktop-side template rendering utility with typed inputs.
- Add per-OS install/uninstall helper scripts that:
  - render descriptors from template contract
  - register/unregister with native OS manager
  - default to user scope

Acceptance target:
- Service can be installed, started, stopped, and removed independently of the desktop UI process.

Delivered implementation:
- Added versioned descriptor templates:
  - `linux.systemd-user.service.tmpl`
  - `macos.launchagent.plist.tmpl`
  - `windows.task.xml.tmpl`
- Added reusable renderer module + CLI:
  - `apps/desktop/main/service_install_templates.js`
  - `apps/desktop/main/render_service_template.js`
- Added installer helpers:
  - `scripts/background_service/install_linux_user_service.sh`
  - `scripts/background_service/uninstall_linux_user_service.sh`
  - `scripts/background_service/install_macos_launchagent.sh`
  - `scripts/background_service/uninstall_macos_launchagent.sh`
  - `scripts/background_service/install_windows_task.ps1`
  - `scripts/background_service/uninstall_windows_task.ps1`
- Added unit coverage for template rendering behavior:
  - `apps/desktop/main/service_install_templates.test.js`

## 12. W5 Packaged One-Click Runtime Wiring (March 2026)
Objective:
- Ensure installed desktop runtime resolves and launches bundled service binary automatically, without manual environment variable setup.

Design constraints:
- Preserve explicit operator override via `SMAP_SERVICE_BIN`.
- Keep source-mode developer workflow unchanged.
- Keep startup logic modular/testable (single resolver utility).

Chosen approach:
- Add dedicated service binary resolver in desktop main process.

## 13. W7 Wizard Opening UX Stabilization (March 2026)
Objective:
- Remove first-impression friction where the Broker Provider dropdown appears non-functional while the wizard gate is active.

Problem details:
- Current mandatory lock disables almost all controls before checks pass.
- This includes Broker Provider selection on the opening screen, which users interpret as a broken dropdown.
- If provider loading fails or returns no items, the select appears blank without actionable context.

Chosen UX behavior:
- Keep mandatory wizard gate intact for mutating actions (saving credentials, running workspace actions).
- Allow non-mutating provider discovery controls while locked:
  - Broker Provider dropdown
  - Reload button
- Add explicit fallback states:
  - "No providers available" when the provider list is empty.
  - "Provider list unavailable" when service/API fetch fails.
- Keep contextual helper text clear that workspace remains locked until wizard checks pass.

## 14. W3 Wizard Install Assistant (March 2026)
Objective:
- Upgrade wizard from passive CLI check-only UX to guided install UX that asks user subscription ownership and chosen CLI install target.

Functional behavior:
- Wizard asks:
  - which subscription(s) user has
  - which CLI user wants to install now
- Wizard validates install target against declared subscription ownership.
- Wizard generates OS-aware install plan and can run install command via embedded terminal in advanced mode.
- Wizard keeps mandatory check gate intact; user still runs checks after install/auth.

Constraints:
- Avoid silent auto-installs without user intent.
- Keep install flow transparent (show command + next steps).
- Preserve compatibility with non-Electron preview mode by showing plan text even if terminal bridge is unavailable.
- Resolution order:
  1. `SMAP_SERVICE_BIN` env override
  2. packaged resource path candidates under Electron `process.resourcesPath/service/`
  3. repo local dev binary (`apps/service/dist/smap-service[.exe]`) when running unpackaged
  4. fallback to Python uvicorn command for source-only environments
- Wire resolver output into startup spawn path with concise diagnostics.

Acceptance target:
- Packaged installer runtime can start service by launching desktop only (assuming bundled service artifact exists).

Delivered implementation:
- Desktop startup now resolves service launch path using deterministic order:
  - `SMAP_SERVICE_BIN` override
  - bundled installer resource binary
  - local repo `apps/service/dist` binary
  - Python uvicorn fallback
- Wizard now includes background-service checks and an install action.
- Wizard installation path is native and platform-aware in main process:
  - Linux: writes systemd user unit + enables/starts via `systemctl --user`
  - macOS: writes LaunchAgent plist + loads via `launchctl`
  - Windows: writes Task Scheduler XML + creates/runs task via `schtasks`
- Added desktop tests for background-service status probing and resolver behavior.

Delivered implementation:
- Added `main/service_runtime.js` resolver module with deterministic precedence:
  1. `SMAP_SERVICE_BIN` override
  2. bundled packaged resource binary
  3. repo local dist binary
  4. Python uvicorn fallback
- Wired desktop startup path to resolver output in `main/main.js`.
- Added unit coverage in `main/service_runtime.test.js`.

## 13. W7 Artifact Payload Trim (March 2026)
Objective:
- Reduce installer download time by publishing only required final installer artifacts from CI.

Chosen approach:
- Keep build generation unchanged.
- Narrow GitHub Actions upload globs to final installer/update metadata files under `apps/desktop/release`.
- Exclude bulky intermediate/unpacked output trees from artifact uploads.
