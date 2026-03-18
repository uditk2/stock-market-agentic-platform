# Issue 048: FR5-FR8 Signal Quality Calibration

## Problem
Signal foundations are present, but fused scoring is still coarse and not well-calibrated for trend/volatility context.

## Scope
- Add trend-strength and volatility-regime derived features.
- Recalibrate fused-score weighting with bounded deterministic logic.
- Persist added feature fields in `features_json`.
- Add tests for bounds, determinism, and new feature presence.

## Acceptance
- Signals remain deterministic for identical input snapshots.
- Fused score stays in `[0, 1]` and reflects added calibration features.
- Tests pass.
