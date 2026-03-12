# Issue 006 - Packaged Runtime Service Binary Auto-Resolution

## Scope
Implement deterministic service binary resolution in desktop startup so packaged installer runtime works without manual `SMAP_SERVICE_BIN` setup.

## Deliverables
- Desktop main-process resolver utility with explicit precedence order.
- Startup path wiring in `main.js` using resolver output.
- Tests for packaged, env-override, and dev fallback paths.
- Docs update for installer/runtime expectations.

## Resolution Order
1. `SMAP_SERVICE_BIN` environment override.
2. Packaged service binary under `process.resourcesPath/service/`.
3. Local dev binary in repo (`apps/service/dist/smap-service[.exe]`).
4. Source fallback (`python3 -m uvicorn smap_service.main:app --port 8787`).

## Acceptance
- Desktop installer runtime starts service with no manual path setup.
- Existing dev workflow remains valid.
- Desktop and service test suites remain green.

## Status
- Complete.

## Verification
- Desktop tests: `npm test` -> `14 passed`.
- Service tests: `.venv/bin/pytest -q` -> `13 passed`.
