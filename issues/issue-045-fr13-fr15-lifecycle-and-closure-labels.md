# Issue 045: FR13-FR15 Lifecycle Monitoring and Closure Labels

## Problem
FR13-FR15 require monitoring open recommendations, applying close triggers, and persisting closure outcomes as labels.

## Scope
- Evaluate open recommendations against latest market data.
- Apply configurable profit/loss/cutoff close triggers.
- Persist close metadata fields for downstream model/backtest use.

## Acceptance
- Lifecycle job closes qualifying recommendations.
- Closure labels are persisted and queryable in recommendation detail.
- Tests validate trigger and persistence behavior.
