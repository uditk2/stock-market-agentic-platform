# Issue 017: Claude detection parity coverage for wizard CLI checks

## Problem
User requested the same detection reliability treatment for Claude as Codex. PATH hardening is shared, but explicit Claude coverage should be tracked and verified.

## Scope
- Add explicit Claude-focused CLI check tests.
- Validate Claude-only subscription scope behavior.

## Acceptance Criteria
- Test coverage includes Claude version-pass path.
- Test coverage includes `requiredCliIds: ['claude']` scope.
- Desktop test suite remains green.
