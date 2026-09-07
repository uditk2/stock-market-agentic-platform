# Issue 009 - Installer Artifact Size Trim

## Scope
Reduce download payload by publishing only final installer outputs from CI artifacts.

## Deliverables
- `build-installers.yml` uploads only release installer files (no full unpacked folders / extra build trees).
- Artifact policy documented in planning docs.
- Verified size reduction via post-change run artifact metadata.

## Acceptance
- Installer artifacts remain installable and CI green.
- Download payload is materially smaller than previous run baseline.
