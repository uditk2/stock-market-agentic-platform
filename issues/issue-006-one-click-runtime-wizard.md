# Issue 006 - One-Click Runtime Wizard Orchestration

## Scope
Deliver true installer-first UX where setup wizard handles background-service installation and packaged service-path resolution automatically.

## Deliverables
- Packaged service launch resolver (env override -> bundled binary -> dev binary -> python fallback).
- Wizard background-service status checks.
- Wizard action to install background service using native OS manager.
- Desktop tests for resolver and background-service manager behavior.

## Acceptance
- User can install desktop app, run wizard, and complete setup without running separate manual service-install scripts.
