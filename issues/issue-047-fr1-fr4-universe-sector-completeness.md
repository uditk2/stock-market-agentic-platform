# Issue 047: FR1-FR4 Completeness (Universe Coverage + Sector Mapping)

## Problem
FR1-FR4 ingestion foundations are present, but completeness gaps remain:
- symbol universe can shrink if dynamic discovery is partial/unavailable,
- instrument metadata lacks richer sector mapping.

## Scope
- Add curated baseline stock-futures universe.
- Merge dynamic Kotak discovery with curated baseline for deterministic broad coverage.
- Add sector metadata persistence in instrument specs.
- Persist inferred sector during ingestion.
- Add tests for merged-universe behavior and sector persistence.

## Acceptance
- Ingestion symbol request set remains broad and deterministic even when dynamic list is limited.
- Instrument specs persist sector where inferable.
- Test suite remains green.
