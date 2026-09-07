# Issue 040: Fix `/connectors/diagnostics` runtime crash

## Problem
Diagnostics endpoint crashes with `AttributeError` due to invalid runtime market client reference.

## Scope
- Restore stable endpoint behavior.
- Add/keep test coverage for diagnostics path.

## Acceptance
- Service tests pass.
- `/connectors/diagnostics` returns payload without exception.
