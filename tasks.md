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

3. W3 Mandatory AI CLI Wizard Enforcement
- Implement executable detection, version check, and auth/session checks for Codex/Claude CLIs.

4. W4 Embedded Terminal Runtime
- Add PTY-backed terminal panel with safe command profiles and advanced mode toggle.

5. W5 Background Service Installation Layer
- Add OS-specific background mode templates:
  - launchd (macOS)
  - Task Scheduler (Windows)
  - systemd user service (Linux)

6. W6 Real Connector Baseline
- Add production-grade connector skeletons (with retry/backoff and normalized outputs):
  - Kotak market feed client
  - NewsAPI client
  - RSS poller/parser
  - NSE announcements adapter
- Slice status:
  - Slice 1 complete: connector scaffolds + retry/backoff + scheduler wiring + baseline tests.
  - Slice 2 complete: provider-specific credential validation + connector diagnostics telemetry + API validation errors.
  - Slice 3 pending: richer connector observability/run-history attribution and integration smoke coverage.

7. W7 CI Packaging Hardening
- Extend GitHub Actions to assemble service+desktop outputs per OS and publish versioned artifacts.

8. W8 Integration and Ops Readiness
- Add integration smoke tests, scheduler recovery tests, and updated runbooks.

9. W9 GitHub Issue Sync and Tracking
- Create/update GitHub issues mapped to W1-W8 and close completed items incrementally.

## Deferred Questions (queued in awaiting registry)
- DQ1: Final default RSS feed list.
- DQ2: Minimum supported OS versions for installer policy.
