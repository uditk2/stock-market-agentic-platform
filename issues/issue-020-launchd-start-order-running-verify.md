# Issue 020 - macOS launchd installed=true but running=false after wizard install

## Problem
Users report launchd background service state as `installed=true` and `running=false` after installer flow. This leaves provider API calls unavailable and creates onboarding dead-ends.

## Scope
- Desktop main-process background service manager only.
- macOS launchd install/start sequencing and running-state verification.
- Unit coverage for darwin status and install flow.

## Acceptance Criteria
- Installer path uses deterministic launchd order (`bootout/bootstrap` then `kickstart`).
- Post-install status verification retries briefly and fails install when service never reaches running.
- Darwin status parser identifies running process using both `state = running` and non-zero `pid` output.
- Desktop unit tests cover the new darwin behavior.

## Out of Scope
- Service binary crash root-cause debugging.
- Notarization/signing changes.
- Linux/Windows service manager behavior changes.
