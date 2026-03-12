# Issue 016: Wizard false Codex detection and provider recovery while blocked

## Problem
Users report Codex is installed but wizard shows `installed=false`, and provider list cannot be configured when service is installed but not running.

## Scope
- Improve CLI check PATH resolution for GUI app environment.
- Keep service start/refresh controls usable while workspace remains locked.
- Add provider-load retry with one-time service auto-start attempt.

## Acceptance Criteria
- Codex detection succeeds in common mac GUI PATH scenarios.
- Provider configuration can recover after starting service from locked state.
- Desktop tests pass and CI remains green.
