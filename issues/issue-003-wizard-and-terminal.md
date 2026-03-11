# Issue 003 - W3 + W4 Wizard and Embedded Terminal

## Scope
Implement mandatory AI CLI setup checks and PTY-backed terminal integration.

## Deliverables
- Wizard checks for CLI presence/version/auth state
- Terminal panel with safe command profiles and advanced mode toggle
- IPC bridge and service-safe execution policy

## Acceptance
- Wizard blocks completion until mandatory checks pass
- Terminal runs profile commands and streams output
