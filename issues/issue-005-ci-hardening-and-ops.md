# Issue 005 - W7 + W8 + W9 CI Hardening, Ops, and Tracking

## Scope
Finalize build hardening, integration checks, and issue-tracking sync.

## Deliverables
- Hardened multi-OS packaging workflow
- Integration smoke tests and scheduler recovery tests
- Runbook updates
- GitHub issue status sync across W1-W9

## Acceptance
- CI publishes expected artifacts per OS
- Tests cover core runtime and background job lifecycle

## Progress
- Identified cross-matrix CI packaging failure root cause:
  - `Build Installers` failed on macOS/Ubuntu/Windows at service binary build step with:
    - `Spec file smap_service.spec not found`
- Applied build hardening fix:
  - Updated `scripts/build_service.sh` to use deterministic absolute spec path and explicit work/dist paths.
  - Added fast-fail guard when spec path is missing.
