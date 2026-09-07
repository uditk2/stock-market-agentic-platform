# Issue 037: Close (x) controls disabled while workspace is locked

## Summary
Close controls (`x`) for modal/toast are not usable when workspace lock state is active.

## Problem
The lock manager disables generic buttons, which inadvertently affects close controls used to dismiss UI overlays.

## Scope
- Ensure close controls remain operable regardless of workspace lock state.
- Add explicit lock bypass ids for modal and toast close buttons.

## Acceptance Criteria
- Settings modal `x` closes modal in locked and unlocked states.
- Toast `x` dismisses toast in locked and unlocked states.
- No regression in other workspace lock behavior.
