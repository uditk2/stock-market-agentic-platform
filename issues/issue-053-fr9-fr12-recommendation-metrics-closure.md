# Issue 053: FR9-FR12 Recommendation Metrics Closure

## Problem
Publish guardrails are calibrated, but operational metrics for recommendation quality/suppression are not explicitly exposed.

## Scope
- Add recommendation metrics aggregation over persisted rows.
- Expose `/recommendations/metrics` route.
- Include suppression reason distribution.
- Add route tests.

## Acceptance
- Metrics route returns status counts and suppression reasons.
- Tests pass and issue #42 can be closed.
