# Issue 014: Unsigned macOS install recovery flow (no notarization credentials)

## Problem
Apple notarization credentials are unavailable, so some users hit Gatekeeper/quarantine launch blocks on macOS.

## Scope
- Add a deterministic helper script to remove quarantine flag from installed app.
- Document exact user commands in README for recoverable install path.

## Acceptance Criteria
- Script exists: `scripts/macos/unblock_unsigned_app.sh`.
- README contains copy-paste recovery command and local script usage.
- CI remains green after change.
