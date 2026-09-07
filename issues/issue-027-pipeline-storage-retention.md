# Issue: Pipeline storage cleanup + automated retention

## Summary
`Build Installers` workflow fails at artifact upload due to GitHub Actions artifact storage quota exhaustion.

## Scope
- Perform one-time cleanup now to recover storage.
- Add scheduled workflow to retain only latest 3 `Build Installers` runs.

## Acceptance Criteria
- Immediate storage cleanup completes successfully.
- New scheduled workflow exists and is valid.
- Workflow keeps only latest 3 runs of `Build Installers`.
- CI no longer fails solely due to historical storage accumulation.

## Notes
- Deleting old workflow runs also removes associated artifacts/logs.
