# Stock Market Agentic Platform
## Design Document
Version 1.2 | March 2026

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
