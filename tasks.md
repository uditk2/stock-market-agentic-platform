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

## Iteration 13 (W5 Runtime Wiring Draft)
1. Define deterministic service binary resolution order for packaged desktop runtime.
2. Add resolver utility module to avoid hardcoded startup assumptions.
3. Wire startup path to use resolved bundled binary before source-mode fallback.
4. Add tests covering packaged and development resolution branches.

## Iteration 14 (W5 Runtime Wiring Refined)
1. Keep `SMAP_SERVICE_BIN` override highest priority for operator control.
2. Keep startup fallback to `python3 -m uvicorn ...` only when packaged binary is unavailable.
3. Surface startup diagnostics in logs for easier support.
4. Re-run desktop + service tests before closing runtime wiring slice.

## Iteration 15 (W7 Artifact Trim Draft)
1. Remove bulky non-installer outputs from uploaded CI artifacts.
2. Keep only final installer/update metadata files in `apps/desktop/release`.
3. Verify post-change artifact size reduction after green CI run.

## Iteration 16 (Wizard Opening UX Draft)
1. Diagnose why Broker Provider dropdown appears broken on first wizard screen.
2. Keep mandatory wizard gate but unblock non-mutating provider discovery controls.
3. Add empty/error fallback option states for provider loading.
4. Preserve clear user messaging for lock state and next steps.

## Iteration 17 (Wizard Opening UX Refined)
1. Keep `providerSelect` + `loadProviderBtn` active while locked; keep save/edit controls locked.
2. Ensure provider schema/status rendering handles empty options safely (no invalid schema request).
3. Add deterministic fallback text for service-down and no-provider states.
4. Re-run desktop + service tests before closeout.

## Iteration 18 (Wizard Install Assistant Draft)
1. Add wizard controls to capture subscription ownership and install target CLI.
2. Add main-process install-plan module to validate choices and generate platform-aware commands.
3. Expose install-plan flow through preload bridge and renderer action button.
4. Run install command through embedded terminal advanced mode with explicit next-step guidance.

## Iteration 19 (Wizard Install Assistant Refined)
1. Keep subscription/CLI compatibility validation deterministic and user-visible.
2. Keep install flow explicit (show selected target + command intent + auth follow-up reminder).
3. Add unit tests for install-plan validation and command generation.
4. Re-run desktop + service tests before CI push.

## Iteration 20 (Wizard Reliability + Stepper Draft)
1. Reproduce mandatory-check failures on current machine and capture failing probe commands.
2. Patch CLI check engine to support subscription-scoped required checks.
3. Update stale auth probes (Codex command compatibility).
4. Add provider-load startup retry and step-by-step wizard Next flow.

## Iteration 21 (Wizard Reliability + Stepper Refined)
1. Keep deterministic pass criteria for selected subscription scope only.
2. Ensure provider dropdown auto-recovers after service warmup (no manual reload requirement for first success path).
3. Keep wizard guidance sequential with one clear next action at each stage.
4. Re-run desktop + service tests, push, and verify installer CI matrix green.

## Iteration 22 (Artifact Scope Draft)
1. Reproduce current uploaded artifact scope from `Build Installers` workflow.
2. Isolate user-facing installer files needed per OS.
3. Draft OS-specific upload-path split with macOS DMG-only requirement.

## Iteration 23 (Artifact Scope Refined)
1. Split upload steps by `matrix.os` to avoid mixed glob overreach.
2. Keep macOS upload limited to `*.dmg` for user download path.
3. Keep Windows/Linux uploads limited to primary installer outputs.
4. Validate workflow and run CI before handing new artifact link to user.

## Iteration 24 (Unsigned macOS Recovery Draft)
1. Capture unsigned-notarization policy decision.
2. Add deterministic mac unblock helper script.
3. Document exact first-run recovery command for users.

## Iteration 25 (Unsigned macOS Recovery Refined)
1. Keep DMG-only artifact distribution unchanged.
2. Provide both local-script and curl one-liner recovery paths.
3. Push and verify CI remains green after script/docs addition.

## Iteration 26 (Direct DMG Release Draft)
1. Add workflow permissions for release asset upload.
2. Add macOS-only release publish step using stable tag.
3. Add direct DMG release URL in README.

## Iteration 27 (Direct DMG Release Refined)
1. Ensure release publish runs only on push to master/main.
2. Use deterministic asset naming and `--clobber` behavior.
3. Validate workflow and share direct release link after successful run.

## Iteration 28 (Wizard Detection/Provider Draft)
1. Reproduce Codex false-negative detection from mac wizard report.
2. Patch CLI check environment PATH handling for GUI-launched runtime.
3. Ensure provider controls needed for recovery remain usable when locked.

## Iteration 29 (Wizard Detection/Provider Refined)
1. Add one-time service auto-start attempt during provider retry path.
2. Keep mandatory lock for mutating controls while allowing startup/reload actions.
3. Add/adjust tests and verify desktop suite passes before CI push.

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
- Follow-up status: in progress (wizard install assistant flow based on user-declared subscription + selected CLI).
- Follow-up status: in progress (reliability hardening + step-by-step wizard next flow).

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
- Follow-up status: packaged one-click runtime binary auto-resolution complete.

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
- Follow-up status: in progress (artifact payload trim to reduce download size).

8. W8 Integration and Ops Readiness
- Add integration smoke tests, scheduler recovery tests, and updated runbooks.

9. W9 GitHub Issue Sync and Tracking
- Create/update GitHub issues mapped to W1-W8 and close completed items incrementally.

## Deferred Questions (queued in awaiting registry)
- DQ1: Final default RSS feed list.
- DQ2: Minimum supported OS versions for installer policy.

## Iteration 30 (First-Open Progressive Onboarding Draft)
1. Implement first-open staged visibility: setup only, then broker, then home.
2. Replace terminal-driven wizard install with behind-the-scenes main-process installer action.
3. Rewire `Next` flow: CLI checks -> broker setup.
4. Auto-transition to home on successful broker save.

## Iteration 31 (First-Open Progressive Onboarding Refined)
1. Keep Codex/Claude parity in install and detection paths.
2. Keep provider-loading retry to avoid empty-provider race on broker stage.
3. Preserve existing service controls and terminal for home stage only.
4. Add targeted tests for installer execution helper and keep full desktop suite green.

## Iteration 32 (Undefined Port Hotfix Draft)
1. Reproduce provider URL parse failure from user report.
2. Patch service launch metadata to always include valid port.
3. Add renderer fallback guard against invalid launch base URL.
4. Run desktop tests and publish patched installer.

## Iteration 33 (Undefined Port Hotfix Refined)
1. Keep fix minimal to avoid onboarding regression.
2. Add/keep resolver tests asserting returned port.
3. Ensure API base defaults to 18787 when launch data is malformed.
