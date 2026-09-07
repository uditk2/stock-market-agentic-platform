# Issue 010 - Wizard opening screen dropdown UX (Broker Provider)

## Summary
On first load, users perceive the `Broker Provider` dropdown as broken because workspace lock disables it and provider loading has weak empty/error state messaging.

## Problem
- Wizard gate is mandatory (correct), but lock currently disables almost all controls.
- `providerSelect` and `Reload` are disabled before checks pass.
- If provider loading fails/returns empty, the select can appear blank and non-actionable.

## Scope
- Keep mandatory wizard enforcement.
- Allow non-mutating provider discovery controls while locked:
  - `providerSelect`
  - `loadProviderBtn`
- Add explicit fallback states for provider fetch:
  - `No providers available`
  - `Provider list unavailable`
- Keep save/edit actions locked until wizard success.

## Acceptance Criteria
- Dropdown is interactable on opening page, even before wizard pass.
- Reload button is interactable on opening page.
- Save credentials and other workspace-mutating actions remain locked until wizard pass.
- Empty provider list and provider-load failures show explicit placeholder option and helper text.
- Desktop and service tests pass.
- CI installer workflow green after push.

## Notes
- Separate pending decision remains for CLI auto-install UX policy (auto-install-all vs per-tool controls).
