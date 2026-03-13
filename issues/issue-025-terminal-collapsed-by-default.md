# Issue 025 - Keep terminal hidden by default with explicit open control

## Problem
Embedded terminal should not be visible by default on home screen; users need an explicit way to open/close it.

## Scope
- Default terminal panel to collapsed/hidden on home view.
- Add an explicit open/close control in navigation or utility area.
- Preserve existing terminal start/stop/send behavior when panel is opened.

## Acceptance Criteria
- Terminal panel is hidden on initial home load.
- User can open and close terminal using clear UI control.
- Existing terminal profile and command functionality remains operational.
- Desktop tests pass.

## Out of Scope
- Terminal permission model changes.
- Shell profile redesign.
