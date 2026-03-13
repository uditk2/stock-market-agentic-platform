# Issue 022 - Packaged service runtime import failure blocks providers

## Problem
Packaged service binary crashed on launch with `ModuleNotFoundError: smap_service`, preventing provider endpoint availability in Linux validation.

## Scope
- Service entrypoint import strategy.
- PyInstaller spec hidden imports.
- Rebuild and runtime validation against `/health` and `/providers/brokers`.

## Acceptance Criteria
- Packaged binary starts successfully.
- `/health` returns 200 and scheduler metadata.
- `/providers/brokers` returns provider list.
- Service tests remain green.

## Out of Scope
- Desktop UI-level wizard automation in headless host.
- Connector behavior changes.
