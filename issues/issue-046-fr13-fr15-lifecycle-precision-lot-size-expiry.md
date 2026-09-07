# Issue 046: FR13-FR15 Lifecycle Precision (Lot Size + Expiry Cutoff)

## Problem
Current lifecycle logic is baseline-only:
- realized P&L uses fixed `lot_size=1`
- cutoff uses generic elapsed-time rule

This causes correctness drift for NSE F&O recommendation closure outcomes.

## Scope
- Persist futures instrument specs (`symbol`, `lot_size`, `expiry_date`, source metadata).
- Extend Kotak scrip-master parsing to extract lot size and expiry where available.
- Wire spec persistence into ingestion flow.
- Use lot-size-aware P&L in lifecycle close evaluation.
- Use expiry-day IST cutoff rule when metadata exists, with deterministic fallback when it does not.

## Acceptance
- Lifecycle close labels use metadata-aware P&L per lot.
- Expiry-aware cutoff trigger is exercised and test-covered.
- Existing DB files migrate safely and tests pass.
