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

## Progress
- W4 terminal runtime delivered:
  - PTY-backed session manager in desktop main process
  - Preload IPC bridge for start/write/resize/stop + output events
  - Profile-gated safe command mode with explicit advanced mode toggle
  - Renderer terminal panel integrated into desktop workspace
  - Desktop command-policy tests added and passing
- W3 wizard enforcement still pending.
