# Issue 021 - Cross-platform service install must verify running state

## Problem
Post-install verification of service running state was only enforced on macOS, creating inconsistent behavior across Linux/Windows where install could appear successful while service remained unavailable.

## Scope
- Desktop background service manager install verification behavior.
- Linux, macOS, and Windows parity for running-state checks.
- Linux local validation evidence for install path.

## Acceptance Criteria
- All supported platforms perform post-install `running=true` verification with retries.
- Install returns failure when service remains installed but not running after retries.
- Unit coverage includes Linux fail-path and Windows delayed-running pass-path.
- Linux local host validation demonstrates install+running status path.

## Out of Scope
- Full GUI wizard execution in headless Linux host.
- Fixing unrelated service binary packaging/module import failures.
