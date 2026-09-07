# Issue 038: Highlighted buttons non-functional in locked setup stage

## Summary
Users reported highlighted controls (Refresh Data, Search) do not work despite being visible.

## Problem
Workspace lock-state disabled those controls during broker/setup stage, creating a functional dead-end perception.

## Scope
- Keep lock for mutating setup actions.
- Allow safe read/inspect controls to remain interactive in locked stage.

## Acceptance Criteria
- Refresh Data works during locked broker stage.
- Search input/button works during locked broker stage.
- No regression to setup lock enforcement for restricted controls.
