# Issue 049: FR9-FR12 Recommendation Publish Quality Calibration

## Problem
Recommendation contract exists but publish logic is still lenient and can publish weak risk-reward setups.

## Scope
- Improve target construction for better baseline risk-reward.
- Extend guardrails with calibrated quality thresholds.
- Keep suppression reasons explicit and persisted.
- Add tests for new publish/suppress outcomes.

## Acceptance
- Weak setups are suppressed with deterministic reasons.
- Published recommendations meet calibrated thresholds.
- Tests pass.
