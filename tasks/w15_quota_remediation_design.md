# W15 Quota Remediation Design

## Problem Statement
`Build Installers` still fails at artifact upload due to GitHub Actions artifact storage quota even after pruning `Build Installers` run history.

## Required Outcomes
1. Unblock pipeline by freeing enough Actions storage now.
2. Explain why pipeline worked earlier and now fails.

## Constraints
- Keep recent operational history where possible.
- Minimize repeat quota failures.

## Approach
- Perform aggressive repo-wide cleanup:
  - delete all current Actions artifacts,
  - prune workflow runs across workflows, keeping latest 3 per workflow.
- Re-run `Build Installers` and verify upload passes.
- Audit historical runs/artifacts to summarize when quota pressure started.
