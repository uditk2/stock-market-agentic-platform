# Issue 034: `records=0` with success needs cause visibility

## Summary
Users see `success | records=0` without clear cause, making failures indistinguishable from true empty data.

## Problem
- Data status panel prioritizes status/record counts but not actionable error cause.
- Users cannot tell if the issue is provider auth, connector parsing, or true no-data condition.

## Scope
- Include connector/job error cause and verification hints in diagnostics payload.
- Update UI data status panel to show last error and likely remediation.
- Keep summary concise and avoid false “all good” impression when records remain zero repeatedly.

## Acceptance Criteria
- Data panel shows explicit failure cause when present.
- Repeated zero-record runs include connector warning context.
- Users can distinguish empty-market condition vs configuration/API failure.
