# Issue 018: First-open progressive onboarding flow

## Summary
Change startup UX to a staged flow:
1) setup (install/detect Codex/Claude)
2) mandatory checks on Next
3) broker credential entry
4) home screen

## Scope
- Renderer staged visibility and transitions.
- Main-process background CLI install execution and preload bridge.
- Keep provider retry behavior and Codex/Claude parity.

## Acceptance Criteria
- First open shows only setup card.
- Install runs in background and reports success/failure in wizard UI.
- Clicking Next runs mandatory checks and moves to broker stage when pass.
- Saving broker credentials moves user to home workspace.
- Desktop tests pass.
