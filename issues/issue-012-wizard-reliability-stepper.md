# Issue 012 - Wizard reliability hardening + step-by-step next flow

## Summary
Fix wizard failures after CLI install and provide a sequential next-button guided setup path.

## Reproduced Problems
- Mandatory checks failing due stale CLI auth probes:
  - Codex currently supports `codex login status`, not `codex auth status`.
  - Claude auth probe path is unreliable for current CLI invocation model.
- Checks currently evaluate both CLIs unconditionally, even when user selected only one subscription path.
- Provider list may appear unavailable on first load due service warmup race.

## Scope
- Patch `cli_checks` command compatibility for current Codex CLI.
- Scope required checks to selected subscription.
- Add provider loading retry/recovery on boot/wizard path.
- Add wizard stepper `Next` UX so setup is guided in a deterministic sequence.

## Acceptance Criteria
- Codex-only subscription path can pass mandatory checks after Codex install/login.
- Wizard no longer blocks on non-selected CLI subscription path.
- Provider list auto-recovers once service is ready (without user confusion).
- Wizard shows clear next action with a step-by-step progression.
- Desktop and service tests pass.
- CI build installers matrix is green.
