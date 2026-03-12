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

## 8. W6 Connector Baseline (Slice 1, March 2026)
Implemented baseline connector layer with retry/backoff and normalized output contracts:
- Kotak market feed client (credential-aware, graceful fallback when missing token)
- NewsAPI adapter (API-key driven fetch + normalization)
- RSS poller/parser (feed list + retry + XML normalization)
- NSE announcements adapter (JSON endpoint adapter + normalization)

Scheduler wiring updates:
- Market ingestion now uses connector client output instead of pure scaffold ticks.
- Health metadata now includes active market connector identifier.
