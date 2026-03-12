# Issue 019: Provider URL parse failure from undefined service port

## Summary
Provider bootstrap can fail with URL parse error because API base becomes `127.0.0.1:undefined`.

## Scope
- Ensure launch metadata always includes numeric port.
- Add renderer guard/fallback to default service port.
- Validate desktop tests and publish patched build.

## Acceptance Criteria
- No provider fetch call attempts to use `:undefined` port.
- Provider list loads using valid default fallback when metadata is missing.
- Desktop tests pass.
