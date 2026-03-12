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
- Follow-up root causes after first rerun:
  - `apps/service/smap_service.spec` was not tracked due `*.spec` gitignore rule.
  - Windows bash path failed on `.venv/bin/activate`.
- Additional hardening fix:
  - Added gitignore allowlist for `apps/service/smap_service.spec`.
  - Removed shell `source` dependency and switched to cross-platform venv python invocation.
- Final packaging root cause and fix:
  - Ubuntu desktop installer failed at `Build desktop installers` because Debian package metadata was incomplete.
  - Updated `apps/desktop/package.json` with required metadata:
    - top-level `homepage`
    - author as object with `email`
    - `build.linux.maintainer`
- Verification:
  - Local desktop packaging: `npm run dist` succeeded (AppImage + DEB).
  - GitHub Actions `Build Installers` run `22987472765` is green across all matrix jobs:
    - `windows-latest`
    - `ubuntu-latest`
    - `macos-latest`
- Added proactive failure handling automation:
  - New workflow `.github/workflows/ci-failure-guardian.yml`.
  - Trigger: `workflow_run` completion for `Build Installers` with `conclusion == failure`.
  - Actions:
    - Ensure `ci-failure` label exists.
    - Create/update a single `CI Failure Tracker` issue and append failure run details.
    - Optionally send Telegram alert when `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` secrets are configured.
