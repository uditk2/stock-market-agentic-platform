# Tasks - Stock Market Agentic Platform (Sprint 1 Implementation)

## Iteration 1 (Draft)
1. Scaffold monorepo and baseline tooling.
2. Build Python service with scheduler and plugin interfaces.
3. Build Electron shell with service control and setup wizard skeleton.
4. Add packaging config (PyInstaller + electron-builder).
5. Add CI workflow for cross-platform installers.
6. Add docs/tests and push to GitHub.

## Iteration 2 (Refined)
1. Split service work into contracts/core vs scheduler/ingestion.
2. Explicitly separate plugin registries for LLM/news/strategy.
3. Ensure desktop depends on service contracts, not provider implementations.
4. Gate packaging after both service and desktop scaffolds are runnable.
5. Gate GitHub push after CI workflow and docs are in place.

## Final Task List
1. S1 Repository Foundation
- Create monorepo directories, baseline README, and tooling stubs.

2. S2 Service Core and Plugin Contracts
- Implement Python service app skeleton, config, logging, and interfaces (`LLMAdapter`, `NewsProvider`, `StrategyModule`).

3. S3 Scheduler and Ingestion Job Framework
- Implement background scheduler manager, job registry, job history persistence stubs, and ingestion job skeletons (market/news/rss/announcements).

4. S4 Desktop Shell and Runtime Bridge
- Implement Electron shell skeleton with preload IPC, setup wizard view, terminal view shell, and background service manager bridge.

5. S5 Packaging Configuration
- Add PyInstaller spec/build scripts for service.
- Add electron-builder config for desktop installers.

6. S6 CI/CD Packaging Pipeline
- Add GitHub Actions matrix workflow for macOS/Windows/Linux artifact generation and upload.

7. S7 Quality and Runbook
- Add smoke tests/lint entrypoints and developer release/build documentation.

8. S8 GitHub Sync
- Commit code in logical batches and push to GitHub remote.

## Blockers / Deferred Questions
- DQ1: Confirm default RSS feed list.
- DQ2: Confirm repo naming/visibility preference if needed.
