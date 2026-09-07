# Issue 050: FR13-FR15 Calendar Precision Fallback

## Problem
Lifecycle cutoff works with explicit expiry metadata, but fallback behavior is still too generic when expiry metadata is missing.

## Scope
- Add monthly-expiry cutoff inference using last-Thursday IST rule.
- Integrate cutoff precedence: explicit expiry, inferred monthly expiry, elapsed-time fallback.
- Add tests for inferred elapsed/non-elapsed scenarios.

## Acceptance
- Lifecycle cutoff remains deterministic with improved calendar semantics.
- Explicit expiry behavior stays unchanged.
- Tests pass.
