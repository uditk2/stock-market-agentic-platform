# W19 Blueprint - Kotak Neo v2 Connectivity Failover

## Problem Statement
Kotak connector verification currently fails on this server due to dependence on unstable `mnapi`/`cnapi`. User requested v2 repo alignment.

## Constraints and Assumptions
- Existing API/UI posts `access_token` only.
- Must remain read-only (no order APIs).
- Must preserve backward compatibility for environments where legacy endpoints still work.

## Design Alternatives Considered
1. Keep current mnapi-only implementation.
- Rejected: continues to fail with upstream reachability issues.

2. Full adoption of official Python SDK and full login flow.
- Rejected for this slice: requires new credentials and OTP/TOTP flow changes.

3. Hybrid in-house connector with v2-aligned endpoints + fallback.
- Chosen: smallest safe change that addresses immediate connectivity class failures.

## Chosen Architecture
- Single connector class remains owner of Kotak HTTP behavior.
- Introduce endpoint candidate sets for each operation.
- Introduce auth header strategy (`token`, `Bearer token`) and classify failures.
- Reuse existing normalization path for MarketBar output.

## Interfaces / Modules
- `apps/service/src/smap_service/plugins/market/kotak_client.py`
  - Add endpoint candidates and fallback request helper.
  - Update verification, scrip-master, and quote calls to use helper.
- `apps/service/tests/test_connectors_baseline.py`
  - Add/adjust tests for fallback and auth/network error mapping.

## Delivery Plan
1. Implement connector fallback + auth normalization.
2. Add tests for fallback behavior and error classification.
3. Run service tests.
4. Validate diagnostics endpoint behavior on runtime.

## Risks and Open Questions
- Provided token may still be invalid for gateway bearer validation.
- If auth remains invalid post-change, next step is credential-flow augmentation (consumer key + TOTP login session).
