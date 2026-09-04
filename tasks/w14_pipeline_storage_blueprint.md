# W14 Pipeline Storage Blueprint

## Problem Statement
Installer pipeline failures are caused by exhausted artifact storage, not build failures.

## Constraints And Assumptions
- Keep exactly latest 3 `Build Installers` runs.
- Deleting old runs is acceptable to recover storage.
- Daily schedule uses UTC.

## Design Alternatives Considered
1. Make artifact uploads non-blocking.
2. Increase paid quota / wait for recalculation.
3. Automatically prune old workflow runs and artifacts.

## Chosen Architecture
Choose (3): add daily cleanup workflow that deletes old `Build Installers` runs beyond the latest 3; do immediate cleanup now.

## Interfaces / Modules
- New workflow file: `.github/workflows/cleanup-build-runs.yml`
- Uses `actions/github-script` with `actions:write` permission.
- Inputs: workflow file name and keep-count constant.

## Delivery Plan
1. Create/track issue for retention automation.
2. Clean existing stored runs/artifacts now.
3. Add scheduled cleanup workflow and commit.
4. Validate YAML and trigger manual run.

## Risks And Open Questions
- Risk: deleting runs removes logs/artifacts older than retention window.
- Risk: workflow file rename would require updating target workflow name.
- Open: if retention should be status-filtered (e.g., only successful runs).
