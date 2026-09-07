# Issue 024 - Move broker configuration into Settings menu

## Problem
Broker configuration currently occupies the main workspace and should instead be managed inside a dedicated Settings surface.

## Scope
- Add Settings entry point in top navigation.
- Move broker provider select/credentials/save workflow into Settings modal/offcanvas section.
- Keep existing provider API contracts unchanged.
- Keep onboarding compatibility: broker setup step should route user into Settings flow.

## Acceptance Criteria
- Broker controls are not shown in main workspace by default.
- Settings menu exposes broker provider and credentials workflow end-to-end.
- Saving credentials still updates service state and UI status.
- Desktop tests pass.

## Out of Scope
- New credential schemas.
- Multi-account broker profiles.
