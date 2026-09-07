# W15 Quota Remediation Blueprint

## Problem Statement
Quota exhaustion remains after scoped cleanup, indicating broader repository Actions storage accumulation.

## Constraints And Assumptions
- User approved aggressive remediation.
- Deleting old artifacts/runs is acceptable.
- "Correctly check" means provide evidence-backed root-cause timeline.

## Design Alternatives Considered
1. Wait 6-12h for quota recalculation only.
2. Make uploads non-blocking without cleanup.
3. Aggressive cleanup + verification + postmortem.

## Chosen Architecture
Choose (3): immediate global cleanup, then verify with fresh pipeline run and explain regression path.

## Interfaces / Modules
- GitHub API endpoints for artifacts and workflow runs via `gh api`.
- Existing workflow: `Build Installers`.
- Existing retention workflow: `cleanup-build-installers-history.yml`.

## Delivery Plan
1. Track issue for aggressive cleanup + analysis.
2. Execute global cleanup commands.
3. Trigger and monitor `Build Installers`.
4. Collect artifact/run metrics and summarize why earlier runs passed.
5. Report outcome and close tracking issue.

## Risks And Open Questions
- Risk: destructive deletion removes historical debug artifacts.
- Risk: if external org/repo storage quota is still exceeded, cleanup may not be enough.
