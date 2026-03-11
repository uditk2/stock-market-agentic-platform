# Issue 001 - Data Layer and Quality (P1-P3)

## Scope
Implement canonical schema foundations and ingestion pipelines:
- P1 Foundations/FR mapping
- P2 Market+lot-size ingestion
- P3 News+announcement ingestion

## Deliverables
- Schema tables created (including lot_sizes and signal_events)
- Kotak 1m ingestion + lookback policy
- Lot-size effective-dating ingestion
- NewsAPI + Moneycontrol adapter + RSS feed ingestion + NSE announcements ingestion
- DQ checks: freshness, completeness, idempotency

## Acceptance
- FR1-FR4 integration tests passing
- Data source IDs persisted for audit
