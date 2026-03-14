# Issue 033: Kotak Neo API alignment and credential verification

## Summary
Current Kotak connector uses a placeholder endpoint and lacks explicit credential verification feedback.

## Problem
- Market connector is not aligned to current Kotak Neo API paths/headers.
- Users cannot verify whether configured Kotak credential is valid and being ingested.
- Diagnostics show `success` with `records=0` but do not clearly distinguish auth failure vs empty data.

## Scope
- Align Kotak connector base URL and endpoint usage to current official SDK behavior.
- Add credential verification routine (non-order, read-only API check) exposed in diagnostics.
- Surface verification status and last error details in API diagnostics for UI visibility.

## Primary References
- https://github.com/Kotak-Neo/Kotak-neo-api-v2 (official SDK)
- SDK URL/config and quotes implementation (`neo_api_client/settings.py`, `urls.py`, `api/quotes_neo_symbol_api.py`)

## Acceptance Criteria
- Connector uses official Kotak Neo base/API pattern instead of placeholder path.
- Diagnostics includes explicit verification result for configured Kotak credential.
- Auth/endpoint errors are observable in UI diagnostics and logs.
