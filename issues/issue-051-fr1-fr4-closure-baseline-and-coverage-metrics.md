# Issue 051: FR1-FR4 Closure Baseline and Coverage Metrics

## Problem
FR1-FR4 is near-complete but closure still needs explicit minimum universe guarantees and clearer coverage metrics.

## Scope
- Add required macro/index futures to curated baseline guarantees.
- Add coverage attribution metrics: dynamic count, curated count, merged count.
- Add tests for guaranteed inclusion and attribution shape.

## Acceptance
- Required baseline futures are always in ingestion symbol requests.
- Coverage metrics are present and deterministic.
- Tests pass.
