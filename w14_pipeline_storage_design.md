# W14 Pipeline Storage Design

## Problem Statement
GitHub Actions `Build Installers` fails during `actions/upload-artifact` because artifact storage quota is exhausted.

## Scope
- Immediate storage cleanup so blocked pipeline can run.
- Add automated daily retention to keep only the latest 3 `Build Installers` runs.

## Constraints
- Must preserve the most recent 3 runs for debugging and release traceability.
- Must run unattended on schedule.
- Must use repository-scoped GitHub token permissions.

## Assumptions
- "last 3 builds" means last 3 workflow runs of `Build Installers` regardless of status.
- UTC schedule is acceptable unless user requests a specific timezone.

## Decision
- Add a dedicated cleanup workflow with:
  - `schedule` trigger (daily)
  - `workflow_dispatch` trigger (manual)
  - run-retention logic using GitHub API to delete runs older than latest 3.
- Perform one-time manual cleanup now via GitHub API from local environment.
