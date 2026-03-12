# Issue 013: macOS installer artifact should be DMG-only for user delivery

## Problem
The Build Installers workflow uploads mixed desktop release files. For user download handoff, only the macOS `.dmg` is required and extra files create confusion and unnecessary payload.

## Scope
- Split artifact upload paths by matrix OS in `.github/workflows/build-installers.yml`.
- Keep macOS upload as `*.dmg` only.
- Keep Windows and Linux uploads limited to primary installers.

## Acceptance Criteria
- `macos-latest` job artifact contains `.dmg` only.
- `windows-latest` artifact contains installer files only (`.exe`, `.msi`).
- `ubuntu-latest` artifact contains installer files only (`.AppImage`, `.deb`).
- Workflow remains green across matrix.
