# Issue 004 - W5 Background Service Installation Layer

## Scope
Add OS templates/scripts for background service mode.

## Deliverables
- launchd template (macOS)
- Task Scheduler XML template + install script (Windows)
- systemd user service template (Linux)
- install/uninstall helper scripts

## Acceptance
- Service can run in background mode without UI process

## Implementation Plan
1. Add template files for Linux/macOS/Windows descriptors.
2. Add reusable renderer module to materialize templates from runtime inputs.
3. Add install/uninstall helpers:
- Linux: `systemctl --user` unit registration.
- macOS: `launchctl` LaunchAgent registration.
- Windows: `Register-ScheduledTask` with generated XML.
4. Add unit tests for template renderer.
5. Validate with desktop + service test suites and document usage.

## Dependencies
- Requires W4 service/runtime command path conventions to be stable.
- Must complete before final W8 operations runbooks are marked done.

## Status
- Complete.

## Verification
- Desktop tests: `npm test` -> `10 passed`.
- Service tests: `.venv/bin/pytest -q` -> `13 passed`.
