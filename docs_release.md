# Release and Packaging Runbook (Sprint 1)

## Goal
Generate self-contained desktop installers for macOS, Windows, and Linux using GitHub Actions.

## Build Flow
1. Build Python background service binary with PyInstaller.
2. Bundle desktop app with electron-builder including service binary.
3. Upload OS-specific artifacts in GitHub Actions.

## Local Commands
```bash
./scripts/build_service.sh
./scripts/build_desktop.sh
```

## CI Workflow
- File: `.github/workflows/build-installers.yml`
- Trigger: push/pull_request/manual
- Matrix: `ubuntu-latest`, `windows-latest`, `macos-latest`

## Notes
- v1 uses unsigned-first profile for personal/internal distribution.
- Production distribution should add signing and notarization secrets and steps.
