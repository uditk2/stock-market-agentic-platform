# Issue 054 - Kotak v2 endpoint failover and auth normalization

## Problem
Kotak verification depends on `mnapi` path availability. On this server, `mnapi`/`cnapi` frequently fail with timeout/522. User requested alignment with Kotak Neo API v2 repository.

## Scope
- Add v2-aligned endpoint candidates and fallback logic for verification + quote flows.
- Normalize auth attempt strategy (`token` + `Bearer token`) without breaking current `access_token` contract.
- Add tests for fallback and failure classification.

## Acceptance Criteria
- Connector no longer depends on a single Kotak domain for verification/quote paths.
- Timeout/unreachable and invalid-credential conditions are distinctly reported.
- Existing API surface remains backward compatible for broker credential payload.
- Service tests pass.

## References
- https://github.com/Kotak-Neo/Kotak-neo-api-v2
