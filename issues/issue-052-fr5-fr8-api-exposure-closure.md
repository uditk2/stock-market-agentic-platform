# Issue 052: FR5-FR8 API Exposure Closure

## Problem
Signals are persisted and calibrated but not yet exposed through a dedicated route for downstream consumption.

## Scope
- Add `GET /signals/recent` with `limit` support.
- Return persisted signal fields with deterministic ordering.
- Add route tests.

## Acceptance
- Route returns recent persisted signals.
- Tests pass and issue #41 can be closed.
