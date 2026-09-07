# Issue 043: FR5-FR8 Signal Engine Foundations

## Problem
Canonical FR5-FR8 require S/R computation, pattern detection, fused scoring, and stable signal persistence; current implementation had no persisted signal model.

## Scope
- Add baseline deterministic signal computation pipeline.
- Persist stable signal IDs and signal metadata.
- Surface signal job status in diagnostics.

## Acceptance
- Signal job runs in scheduler.
- Signals are persisted with stable IDs.
- Tests validate output determinism and persistence.
