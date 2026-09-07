# Issue: Global Actions storage remediation + root-cause check

## Summary
Even after pruning `Build Installers` history, artifact uploads still fail due to Actions storage quota.

## Scope
- Delete all existing repository artifacts.
- Prune old runs across workflows (keep latest 3 each).
- Rerun `Build Installers` to confirm upload behavior.
- Explain why earlier runs worked and current run failed.

## Acceptance Criteria
- Global cleanup completed.
- Fresh `Build Installers` run outcome captured.
- Root-cause explanation documented and communicated.
