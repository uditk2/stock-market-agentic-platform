# W15 FR1-FR15 Traceability Audit (Functional-Correctness Pass)

Date: 2026-03-14

## Summary
- Functional correctness audit baseline: **not compliant** with full canonical FR1-FR15.
- Immediate runtime defect found: `/connectors/diagnostics` raised `AttributeError` before fix.
- Prior closed issues (#29-#35) mostly addressed UI interaction/accessibility, but do not satisfy most canonical FR requirements.

## FR Coverage Matrix
| FR | Requirement (canonical) | Status | Evidence |
|---|---|---|---|
| FR1 | 1-min OHLCV for all active NSE F&O via Kotak | Partial | `ingestion/jobs.py` currently requests fixed 4 symbols only (lines 23-25). |
| FR2 | Rolling lookback >= 1 month | Missing | No historical bar persistence path in service runtime. |
| FR3 | Lot-size master by symbol/effective date | Missing | No lot-size ingestion/storage module present. |
| FR4 | News + announcements mapped to symbols/sectors | Partial | News/announcements fetch exists, but no symbol/sector mapping persisted (`ingestion/jobs.py` lines 40-73). |
| FR5 | Hybrid swing-volume S/R bands | Missing | No S/R computation module in current service code. |
| FR6 | Pattern detection (breakout/reversal/consolidation/volume spike) | Missing | No technical pattern engine module found. |
| FR7 | Fuse sentiment + announcements + pattern + S/R into score | Missing | No fusion scorer implementation found. |
| FR8 | Stable signal_id persisted | Missing | No signal persistence schema/API. |
| FR9 | Strategy text versioned artifacts | Missing | No strategy artifact persistence endpoints/tables. |
| FR10 | Recommendation fields incl entry/sl/targets/rationale | Partial | `RecommendationService` returns static samples with limited fields (`core/recommendations.py`). |
| FR11 | Recommendation linked to strategy_artifact_id + signal_ids | Missing | No linkage model/table/API found. |
| FR12 | Guardrail gating before recommendation publish | Missing | No guardrail evaluation pipeline in runtime. |
| FR13 | Monitor open recommendations with per-lot P&L | Missing | No open-position lifecycle monitoring implementation. |
| FR14 | Configurable close triggers + expiry cutoff | Missing | No close-trigger engine/config enforcement path. |
| FR15 | Persist closure outcomes as ML/backtest labels | Missing | No closure-label persistence path. |

## Closed-Issue Revalidation Snapshot
- #29 Search/Refresh feedback: implemented (UX only).
- #30 Kotak alignment + verification: partially implemented; verification existed post-save/diagnostics and required pre-save gate.
- #31 records=0 diagnostics visibility: implemented but depended on stable diagnostics route.
- #32 Backtesting visibility: implemented as visible placeholder panel, no backtesting engine.
- #33 ML mode visibility: implemented as visible placeholder panel, no ML recommendation engine.
- #34 close x controls: implemented.
- #35 highlighted locked-stage controls: implemented.

## Correctness Priorities Derived
1. Stabilize core service correctness: diagnostics route + credential verification contract.
2. Enforce pre-save credential verification for Kotak.
3. Define and execute phased implementation slices for missing FR clusters.
