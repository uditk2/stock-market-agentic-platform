# Issue 035: Add Backtesting option visibility in workspace

## Summary
Users do not see any Backtesting option in the current desktop workspace.

## Problem
- Backtesting capability is expected by users but has no visible entry point in current UI.

## Scope
- Add explicit Backtesting section/tab in workspace navigation.
- Provide baseline UI state with clear status (available / in progress) and next actions.
- Keep implementation modular for later engine integration.

## Acceptance Criteria
- Backtesting is visible in main workspace navigation.
- Clicking Backtesting shows a dedicated panel (not hidden/absent).
- Panel communicates current capability status and planned next step.
