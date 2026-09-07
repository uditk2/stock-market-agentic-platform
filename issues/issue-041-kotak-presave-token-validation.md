# Issue 041: Enforce Kotak token validation before credential save

## Problem
Kotak token was previously saved before strong live verification, causing delayed failures.

## Scope
- Validate Kotak token during `/providers/brokers/selection` call.
- Reject save on verification failure and surface reason.

## Acceptance
- Invalid token returns 400 with verification detail.
- Valid token path saves credentials.
- Automated tests cover both pass/fail cases.
