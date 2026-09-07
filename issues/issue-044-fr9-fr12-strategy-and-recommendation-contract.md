# Issue 044: FR9-FR12 Strategy Artifacts and Recommendation Contract

## Problem
FR9-FR12 require free-text strategy versioning, full recommendation fields, signal linkage, and guardrail suppression; current implementation lacked this contract.

## Scope
- Persist strategy artifacts with versions.
- Persist recommendations with FR10 fields and status/suppress_reason.
- Persist recommendation-signal links.
- Enforce baseline publish guardrails.

## Acceptance
- Strategy API accepts and versions free text.
- Recommendation generation persists required fields and links.
- Suppressed recommendations include explicit suppress reason.
