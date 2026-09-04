# W19 Design - Kotak Neo v2 Connectivity Failover

## Problem Statement
Current Kotak verification and market data paths are hardcoded to `mnapi.kotaksecurities.com`. From this server, `mnapi`/`cnapi` frequently timeout or return 522, causing token verification to fail before credential save. The user asked to align with the official Kotak Neo API v2 repository.

## Goals
- Align connector endpoint strategy with official v2 domain/path patterns.
- Remove single-host dependency on `mnapi`.
- Preserve existing API contract for current UI (`access_token`) while improving auth header compatibility.
- Keep changes read-only and limited to credential verification + quote/scrip-master fetch paths.

## Non-Goals
- Implement full Kotak login/TOTP session generation flow in this slice.
- Add order placement/execution APIs.
- Change desktop credential UX schema beyond backward-compatible additions.

## Key Findings Informing Design
- `gw-napi.kotaksecurities.com` responds reliably from this server.
- `mnapi` and `cnapi` are intermittently unreachable from this host.
- v2 paths differ for some endpoints (e.g. `Files/1.0/masterscrip/v2/file-paths`, `apim/quotes/1.0/...`).
- Gateway expects proper bearer/apikey semantics; current token format may still be invalid, but that is an auth issue (not network reachability).

## Constraints and Assumptions
- Existing stored field is `access_token`; must remain supported.
- Service must continue operating if only legacy endpoint works in other environments.
- Network behavior can vary by host; endpoint strategy must be ordered and retry-aware.

## Design Choice
Implement endpoint failover and auth normalization in `KotakMarketFeedClient`:
- Add ordered candidate endpoints for:
  - scrip master path discovery (v2 + legacy variants)
  - quotes fetch (v2 + legacy variants)
- For each request, try candidates until success or terminal auth error.
- Normalize `Authorization` header to try both raw token and `Bearer <token>` where applicable.
- Preserve existing response normalization and downstream contracts.

## Risk Review
- Risk: additional request attempts increase latency.
  - Mitigation: short timeout and bounded retries.
- Risk: auth errors differ by gateway.
  - Mitigation: classify network vs auth failures explicitly.
- Risk: regression in tests relying on older path assumptions.
  - Mitigation: update/add connector tests for candidate fallback order and error classification.
