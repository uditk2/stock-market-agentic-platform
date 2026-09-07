# Issue 011 - Wizard CLI install assistant (subscription-aware)

## Summary
Upgrade setup wizard to actively guide CLI installation by asking user subscription ownership and selected install target, then generating/running install flow using embedded terminal.

## Problem
- Current wizard only reports missing Codex/Claude CLIs.
- Users expect wizard to help install missing tools directly.
- Install intent must respect subscription ownership to avoid confusing paths.

## Scope
- Add wizard controls:
  - subscription ownership selector
  - install target selector (`codex` or `claude`)
  - install action button
- Add main-process install-plan module with:
  - subscription/CLI compatibility validation
  - platform-aware install/auth/check command guidance
- Wire preload + IPC for install-plan requests.
- Renderer executes install command through embedded terminal advanced mode.
- Keep mandatory check gate unchanged.

## Acceptance Criteria
- Wizard asks subscription and chosen CLI target.
- Invalid subscription/target combinations are blocked with clear message.
- Valid selection produces install guidance and executes install command through terminal bridge when available.
- User can re-run mandatory checks after install/auth flow.
- Desktop + service tests pass; CI green.
