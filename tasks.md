# Tasks - Stock Market Agentic Platform (Wave 2 Build Plan)

## Iteration 1 (Draft)
1. Persist scheduler/job state in SQLite.
2. Add configurable provider registry and RSS source catalog.
3. Implement mandatory AI CLI verification flow in setup wizard.
4. Implement in-app terminal with safe command profiles.
5. Add OS background-service installers/templates.
6. Implement first real data-source connectors.
7. Harden CI packaging and release artifacts.
8. Add integration tests and operational docs.
9. Sync GitHub issues to dependency tasks.

## Iteration 2 (Refined)
1. Force persistence first (blocks scheduler reliability and recovery).
2. Split W2 into broker credential UX, recommendation workspace UX, and backend contract tasks.
3. Make wizard gating precede terminal rollout.
4. Keep daemon/service templates before release-hardening.
5. Gate CI release flow on terminal + daemon + connector readiness.
6. Keep issue-sync task last after dependency graph is stable.

## Iteration 3 (W2 UX Refinement)
1. Lock W2 user UX: onboarding `1C`, recommendations-first home, search, tabbed recommendation rationale.
2. Implement broker selection and provider-specific credential capture for Kotak Neo/Upstox/Kite.
3. Keep news source inputs hidden in W2 (defaults only).
4. Add recommendation detail payload contract to support news/technicals/strategy tabs.
5. Resolve credential storage policy (plain vs encrypted) before shipping credential persistence.

## Iteration 4 (W6 Connector Baseline Refinement)
1. Add shared retry/backoff utility and enforce its use in external connector calls.
2. Implement Kotak market connector skeleton with normalized `MarketBar` output contract.
3. Upgrade NewsAPI/RSS/NSE adapters from placeholders to resilient normalized fetch paths.
4. Wire market connector into scheduler ingestion and expose connector identity in health metadata.
5. Add focused connector baseline tests and keep suite green before moving to connector hardening.

## Iteration 5 (W6 Slice 3 Draft)
1. Extend run-history persistence with connector attribution and latency metrics.
2. Propagate attribution metadata from ingestion jobs through scheduler wrappers.
3. Enrich diagnostics with latest connector run snapshots and failure counts.
4. Add scheduler-path integration smoke tests for diagnostics + observability outputs.

## Iteration 6 (W6 Slice 3 Refined)
1. Keep storage migration backward-compatible for existing SQLite files.
2. Ensure `/jobs/history` remains stable while adding `connector`, `duration_ms`, and `attribution`.
3. Add a dedicated observability route for richer run-summary payloads.
4. Require green suite before marking W6 complete.

## Iteration 7 (W4 Terminal Draft)
1. Add a PTY-backed terminal runtime in desktop main process.
2. Expose minimal IPC bridge for session start/write/resize/stop and output events.
3. Add safe command profiles with strict allowlists.
4. Add explicit advanced mode to permit unrestricted commands.
5. Add renderer terminal panel for profile selection, output, and input.

## Iteration 8 (W4 Terminal Refined)
1. Keep default mode profile-restricted; advanced mode must be explicit and visible.
2. Ensure terminal lifecycle cleanup on app close and session restart.
3. Preserve desktop recommendations UX while adding terminal as a separate section.
4. Add focused tests for command gating and profile behavior where practical.

## Iteration 9 (W3 Wizard Draft)
1. Add CLI check engine for codex and claude install/version/auth probes.
2. Expose wizard checks over preload IPC.
3. Add setup wizard UI section with check results.
4. Gate workspace controls until wizard passes.

## Iteration 10 (W3 Wizard Refined)
1. Keep wizard mandatory: no bypass path in baseline W3.
2. Keep checks deterministic with structured diagnostics payloads.
3. Add unit coverage for CLI check engine pass/fail scenarios.
4. Re-run desktop + service tests before marking Issue #3 complete.

## Iteration 11 (W5 Service Install Draft)
1. Define a reusable template contract for Linux, macOS, and Windows service descriptors.
2. Add a renderer utility to materialize templates from typed inputs.
3. Add install/uninstall scripts for systemd user units, launchd LaunchAgents, and Task Scheduler jobs.
4. Keep scripts user-scoped by default to avoid admin-only workflows.

## Iteration 12 (W5 Service Install Refined)
1. Keep service command/args configurable to support both packaged binaries and source-mode runtime.
2. Add unit tests for template rendering to prevent descriptor drift.
3. Ensure helper scripts are idempotent and safe to rerun.
4. Re-run desktop + service tests before marking W5 complete.

## Final Task List
1. W1 Persistent Runtime State
- Replace in-memory scheduler/job history with SQLite-backed persistence and recovery metadata.

2. W2 Provider and Feed Configuration
- Implement broker selection UX (Kotak Neo, Upstox, Kite) with provider-specific credential forms.
- Persist provider credentials in SQLite via a dedicated service module.
- Hide news source user inputs in W2 and keep system-managed defaults.
- Implement recommendations-first daily view with:
  - instrument search bar
  - click-through recommendation details in tabbed rationale view (news, technicals, strategy).
- Polish interface with industry-standard UX patterns and library-backed components.

3. W3 Mandatory AI CLI Wizard Enforcement
- Implement executable detection, version check, and auth/session checks for Codex/Claude CLIs.
- Status: complete (CLI check engine, preload bridge, mandatory renderer wizard gate, tests).

4. W4 Embedded Terminal Runtime
- Add PTY-backed terminal panel with safe command profiles and advanced mode toggle.
- Status: complete (main-process PTY manager, preload IPC bridge, renderer terminal panel, command policy tests).

5. W5 Background Service Installation Layer
- Add OS-specific background mode templates:
  - launchd (macOS)
  - Task Scheduler (Windows)
  - systemd user service (Linux)
- Add install/uninstall helpers for each OS template.
- Status: complete (template renderer, per-OS install/uninstall helpers, and renderer tests delivered).

6. W6 Real Connector Baseline
- Add production-grade connector skeletons (with retry/backoff and normalized outputs):
  - Kotak market feed client
  - NewsAPI client
  - RSS poller/parser
  - NSE announcements adapter
- Slice status:
  - Slice 1 complete: connector scaffolds + retry/backoff + scheduler wiring + baseline tests.
  - Slice 2 complete: provider-specific credential validation + connector diagnostics telemetry + API validation errors.
  - Slice 3 complete: richer connector observability/run-history attribution and integration smoke coverage.

7. W7 CI Packaging Hardening
- Extend GitHub Actions to assemble service+desktop outputs per OS and publish versioned artifacts.

8. W8 Integration and Ops Readiness
- Add integration smoke tests, scheduler recovery tests, and updated runbooks.

9. W9 GitHub Issue Sync and Tracking
- Create/update GitHub issues mapped to W1-W8 and close completed items incrementally.

## Deferred Questions (queued in awaiting registry)
- DQ1: Final default RSS feed list.
- DQ2: Minimum supported OS versions for installer policy.
