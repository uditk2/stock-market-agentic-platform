# Issue 001 - W1 Persistent Runtime State

## Scope
Move scheduler/job state from in-memory storage to SQLite-backed persistence.

## Deliverables
- SQLite schema for job runs, schedule metadata, recovery cursor
- Runtime repository layer + migrations bootstrap
- Scheduler startup recovery path and catch-up metadata

## Acceptance
- Service restart preserves prior run history
- Recovery metadata available via API
