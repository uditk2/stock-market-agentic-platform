# Issue 002 - W2 + W6 Provider and Connector Baseline

## Scope
Implement W2 provider/feed UX + credential persistence and W6 connector baseline.

## Deliverables
- Broker choice UX for:
  - Kotak Neo
  - Upstox
  - Kite
- Provider-specific credential capture and SQLite persistence
- Recommendations-first daily view with F&O search
- Tabbed recommendation detail view:
  - news influence
  - technical indicators
  - strategy rationale
- Config-driven provider registry
- System-managed default news sources (no user news input in W2)
- Connector skeletons with retry/backoff: Kotak, NewsAPI, RSS, NSE announcements

## Acceptance
- Providers can be enabled/disabled via config
- Users can save broker credentials and reopen app with provider selection retained
- Recommendation detail tabs render structured explanation payloads
- Connector calls are normalized and logged

## Locked Decisions
- Credential storage policy: encrypted at rest in local SQLite.
- Daily home scope: recommendations + search only in W2.
- Default recommendation ordering: confidence (descending).

## Progress
- W2 delivered and verified.
- W6 slice 1 delivered:
  - shared retry/backoff utility
  - Kotak market connector skeleton
  - NewsAPI/RSS/NSE adapters upgraded from placeholders
  - scheduler market-ingestion connector wiring
  - baseline tests passing
- W6 slice 2 delivered:
  - provider-specific required credential field templates
  - validation failures returned as structured 400 API responses
  - connector diagnostics endpoint for market/news readiness snapshot
  - test suite expanded and passing
- W2 UX polish delivered:
  - Bootstrap 5 + Bootstrap Icons based interface refresh
  - standardized cards/forms/tabs/toasts patterns
  - improved recommendation list/detail interaction and validation feedback
- W6 slice 3 delivered:
  - job history now records connector attribution + duration + metadata context
  - `/jobs/history` returns connector-attributed run details
  - diagnostics enriched with latest run snapshots and scheduler failure counters
  - new `/connectors/observability` endpoint with aggregate + recent run payloads
  - integration smoke test added for scheduler-path attribution + diagnostics
