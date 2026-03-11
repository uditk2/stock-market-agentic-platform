# Canonical Plan Extracted from Uploaded DOCX

Source: /home/azureuser/connector/winter_coding_bot/uploads/doc_gzyll6bw.docx

Stock Market Agentic Platform
Design Document
Version 1.1  |  March 2026
1. Problem Statement
Indian retail traders participating in NSE F&O (Futures & Options) markets face three compounding challenges when making trading decisions:
The Stock Market Agentic Platform addresses all three challenges. It is an AI-agent-driven system that ingests multi-source signals daily, correlates them across the NSE F&O futures universe (~180–200 stocks), generates precise trade recommendations (entry, stop loss, and target), monitors outcomes, and feeds results back into the agent to continuously improve the quality of level prediction.
2. Scope
3. Functional Requirements
The following FR1–FR15 are testable requirements mapped to implementation tasks. Each must be verifiable via integration tests in P10.
3.1 Data Ingestion
3.2 Screening and Signal Generation
3.3 Strategy and Recommendation
3.4 Monitoring and Feedback
4. Key Constraints and Assumptions
5. Architecture and Design Decisions
5.1 Locked Decisions
Decision 1 — Data Provider and Reliability
Kotak Neo is the exclusive market data feed for v1.
Required reliability controls: request cache, retry with exponential backoff, feed-freshness checks, stale-data alerts, and global kill switch.
Decision 2 — Support / Resistance Method
Hybrid weighted swing + volume method.
Detect swing highs/lows, weight by number of touches and relative volume, cluster nearby levels, and retain the top support/resistance bands.
Decision 3 — Expiry Handling (No Rollover)
Rollover is disabled in v1.
Open recommendations are closed at T−1 day or same-day based on a configured cutoff window.
A close-then-open cycle is treated as a new recommendation, not a rollover continuation.
Decision 4 — Strategy Input Model
Free-text strategy input is always accepted; no hard enforcement gate.
System may optionally derive structured tags from free text for analytics and search.
Decision 5 — Learning Model
Supervised learning for v1; RL deferred.
Learns strategy applicability by stock, sector, and market regime.
Mandatory storage: versioned strategy rule artifacts, recommendations generated from those rules, and realized outcomes.
Backtesting must run against stored strategy artifacts, not ad-hoc text.
5.2 Design Alternatives Rejected
5.3 Chosen Architecture
The platform is structured in seven layers, each with explicit ownership and dependencies:
5.4 Data Source Resolution (v1)
5.5 Market Regime Definition
Regime is computed from index-level and symbol-level indicators at recommendation time and stored as a single composite field (format: trend_regime|vol_bucket, e.g. bull|high).
6. Database Schema
Minimum required schema. All tables use surrogate integer primary keys unless stated. Timestamps are UTC.
7. Core API Interfaces
8. Non-Functional Requirements
9. Acceptance Criteria
Design is considered complete and implementation-ready when all of the following are satisfied:
FR1–FR15 are testable, each mapped to at least one implementation task and one integration test in P10.
Default P&L close thresholds (₹20k profit / ₹30k loss) are explicitly documented and confirmed configurable.
Market regime definition is explicit and machine-computable (trend × volatility buckets).
DB schema includes lot sizes, strategy artifacts, outcomes, and recommendation-signal linkage.
Data source stack is specified for market data, news, and announcements.
All locked decisions (1–5) are reflected consistently across design, blueprint, tasks, and dependency graph.
10. Delivery Plan
11. Tasks and Dependencies
11.1 Final Task List
11.2 Task Dependencies
11.3 Execution Order
12. Risks and Mitigations
13. Open Questions
The following items are not yet resolved and are required before the referenced tasks can be built. Each must be closed before the dependent task enters development.
OQ1 — Cost / Slippage Methodology (blocks P7)
CostSlippageEngine is referenced in the Backtest Layer (P7) but no methodology is defined. Without explicit assumptions, backtesting results will not be realistic or comparable across runs. The following must be specified before P7 enters development:
OQ2 — Supervised Model Lifecycle (blocks P8)
P8 covers training and inference for the applicability model, but the lifecycle around model versioning, promotion, and retraining is undefined. The model_version field exists in the applicability_scores schema, but without answers to the following questions P8 cannot be built to a testable specification:

## Table 1
Challenge | Description
Signal fragmentation | Geopolitical news, NSE announcements, fundamental results, and technical patterns exist in silos. No single tool ingests and correlates all four signals to surface actionable futures trades.
Strategy opacity | A trader's intuition — the personal strategy governing when and where to enter or exit — is never formally captured, cannot be back-tested, and cannot improve over time.
No feedback loop | Trade outcomes are never tied back to the signals and levels that generated the recommendation. There is no mechanism for the system to learn from wins and losses over time.

## Table 2
In Scope | Out of Scope
✓ NSE F&O eligible stocks (futures only) | ✓ Monthly expiry futures contracts | ✓ Daily signal ingestion and screening | ✓ Agent-generated trade recommendations | ✓ Automated outcome monitoring and backtesting | ✓ Agent feedback loop and level tuning | ✗ Options trading (calls, puts, spreads) | ✗ Cash / equity segment | ✗ Automated order execution / broker integration | ✗ Portfolio-level position sizing | ✗ Index futures (Nifty, Bank Nifty) | ✗ Reinforcement learning policy optimization (v1)

## Table 3
FR | Requirement
FR1 | Ingest 1-minute OHLCV futures bars for all active NSE F&O stock symbols via Kotak Neo APIs.
FR2 | Maintain minimum rolling historical lookback of 1 month for screening features; target 3 months when storage permits.
FR3 | Ingest and version the NSE lot-size master by symbol and effective date; update whenever NSE publishes changes.
FR4 | Ingest news and corporate announcements with source IDs and timestamps; map each item to relevant symbols and sectors.

## Table 4
FR | Requirement
FR5 | Compute hybrid weighted swing-volume support/resistance bands per symbol; cluster nearby levels and retain top bands.
FR6 | Detect technical patterns for each shortlisted stock: breakout, reversal, consolidation, and volume spike.
FR7 | Fuse sentiment scores, announcement impact, pattern signals, and S/R proximity into a ranked shortlist score.
FR8 | Assign every generated signal a stable signal_id and persist it for downstream audit linkage.

## Table 5
FR | Requirement
FR9 | Accept and store user strategy text as versioned strategy artifacts; free-text input must always be accepted without hard rejection.
FR10 | Generate recommendation fields: direction (long/short), entry price, stop-loss, target 1, target 2 (optional), confidence, and rationale.
FR11 | Link each recommendation to its strategy_artifact_id and the contributing signal_ids[] via recommendation_signal_links.
FR12 | Publish a recommendation only when all data-quality and risk guardrails pass; suppress with logged reason otherwise.

## Table 6
FR | Requirement
FR13 | Monitor all open recommendations continuously; compute per-lot P&L using the current effective lot size for the symbol.
FR14 | Apply configurable close triggers with explicit defaults: profit ≥ ₹20,000 per lot → close; loss ≤ ₹−30,000 per lot → close. Close open recommendations at T−1 day or same-day cutoff window at expiry (no rollover in v1).
FR15 | Persist closure outcomes (close reason, close price, realized P&L per lot, closed_at) as labels for backtesting and supervised-learning training.

## Table 7
Area | Constraint / Assumption
Instrument | System covers NSE F&O eligible stocks, futures segment only. Index futures (Nifty, Bank Nifty) and options are excluded from v1.
Universe | Stock universe is defined by SEBI’s current F&O eligibility list (~180–200 stocks). The list shall be refreshed whenever SEBI publishes updates.
Lot sizes | Per-stock lot sizes as published by NSE shall be stored with effective dating and updated in the database. P&L thresholds (₹20k/₹30k) are evaluated in absolute rupee terms per lot.
Data source | Kotak Neo is the only market data source in v1 (1-min bars, LTP, lot-size master). Yahoo Finance is permitted for exploratory research only and must never be used as a canonical intraday futures source.
Execution | The system generates recommendations only. It does not place, modify, or cancel orders. Execution remains the trader’s responsibility.
Expiry cycle | All futures positions are treated as monthly contracts. Weekly-expiry stocks follow the same close-at-expiry rules. No rollover logic is implemented in v1.
Compliance | Recommendations are for personal use only. Distribution of signals to third parties may require SEBI registration as an Investment Advisor.

## Table 8
Alternative | Reason Rejected
LLM-only recommendation generation | Insufficient determinism and auditability.
Strict DSL-only strategy enforcement | Conflicts with free-text-always-valid requirement.
RL-first learning loop | Sample inefficiency, delayed reward complexity, and operational risk in v1.

## Table 9
Layer | Components
Data Layer | KotakMarketIngestor (1m bars), LotSizeMasterIngestor, NewsIngestor (NewsAPI + Moneycontrol adapter), NSEAnnouncementIngestor, DataQualityGuard
Signal Layer | SentimentScorer, SectorImpactMapper, WeightedSwingVolumeSR, TechnicalPatternDetector (breakout / reversal / consolidation / volume spike)
Strategy Layer | StrategyArtifactStore (versioned free-text artifacts), Optional StrategyTagger
Recommendation Layer | RecommendationGenerator, RiskGuardrails, SignalTrailLinker
Lifecycle Layer | PositionMonitor (per-lot P&L), ExpiryCloseManager (T−1/same-day, no rollover), OutcomeRecorder
Backtest Layer | StrategyArtifactBacktester (uses stored artifacts), CostSlippageEngine
Learning Layer | RegimeComputer, StrategyApplicabilityTrainer (supervised), StrategyApplicabilityInferencer
Delivery Layer | TelegramNotifier, HistoryQueryAPI

## Table 10
Data Type | Source
Market candles and LTP | Kotak Neo APIs
Lot-size master | Kotak Neo / NSE published lot-size table (effective-dated)
Corporate announcements | NSE corporate announcements feed (official source)
News — primary | NewsAPI (broad market and company news coverage)
News — secondary | Moneycontrol adapter (where NewsAPI coverage is insufficient)

## Table 11
Dimension | Value | Condition
Trend regime | Bull | Close above 50 EMA and 50 EMA slope positive
Trend regime | Bear | Close below 50 EMA and 50 EMA slope negative
Trend regime | Sideways | Neither bull nor bear criteria met
Volatility bucket | Low / Medium / High | Rolling 14-period ATR percentile at symbol level

## Table 12
symbols | Fields
Columns | symbol_id, ticker, company_name, sector, is_fo_active, created_at, updated_at

## Table 13
lot_sizes | Fields
Columns | symbol_id (FK), lot_size, effective_from, effective_to, source, updated_at

## Table 14
market_bars_1m | Fields
Columns | symbol_id (FK), contract_month, ts, open, high, low, close, volume, oi, source

## Table 15
news_events | Fields
Columns | news_id, source_name, source_item_id, published_at, title, summary, url

## Table 16
announcement_events | Fields
Columns | announcement_id, source_item_id, published_at, title, url, category

## Table 17
signal_events | Fields
Columns | signal_id, symbol_id (FK), ts, signal_type, signal_payload_json, score, source_refs_json

## Table 18
strategy_artifacts | Fields
Columns | strategy_artifact_id, version, raw_text, parsed_tags_json, author, status, created_at

## Table 19
recommendations | Fields
Columns | recommendation_id, strategy_artifact_id (FK), symbol_id (FK), contract_month, direction, entry, stop_loss, target_1, target_2, confidence, rationale, regime, created_at

## Table 20
recommendation_signal_links | Fields
Columns | recommendation_id (FK), signal_id (FK)  [junction table — enforces FR11 audit trail]

## Table 21
recommendation_outcomes | Fields
Columns | recommendation_id (FK), close_reason, close_price, pnl_per_lot, closed_at, expiry_bucket

## Table 22
applicability_scores | Fields
Columns | strategy_artifact_id (FK), symbol_id (FK), sector, regime, score, model_version, generated_at

## Table 23
Method | Endpoint | Description
POST | /strategies | Store a new strategy text as a versioned artifact
GET | /strategies/{id} | Retrieve a strategy artifact by ID
POST | /recommendations/generate?as_of=... | Generate recommendations as of a given timestamp (deterministic replay)
GET | /recommendations/open | List all currently open recommendations
GET | /recommendations/{id}/signals | Fetch all signal links for a recommendation
POST | /monitor/run | Trigger a monitoring cycle to evaluate open recommendations
POST | /backtests/run | Run a backtest against a stored strategy artifact (requires artifact id/version)
POST | /learning/train-supervised | Trigger supervised applicability model training
GET | /learning/applicability?symbol=...&sector=...&regime=... | Query strategy applicability scores

## Table 24
Requirement | Specification
Deterministic replay | Recommendation generation and backtests must produce identical output when run with the same as_of timestamp and input snapshot.
End-to-end audit trail | Every recommendation must be traceable: source event → signal → strategy artifact → recommendation → outcome.
Idempotency | Ingestion and monitoring jobs must be safe to re-run; duplicate runs must not create duplicate records.
Observability | Metrics required: feed freshness per symbol, signal generation counts, publish-suppression reasons, job failure counts, and P&L threshold breach events.

## Table 25
Phase | Scope
Phase 1 | Data, Signals | & Strategy | FR1–FR10. Kotak ingestion, lot-size master, news/announcement ingestion, signal engines (S/R, patterns, sentiment), strategy artifact store, recommendation generation with guardrails and signal-trail linkage.
Phase 2 | Monitoring | & Backtesting | FR11–FR15. Signal linkage enforcement, per-lot P&L monitoring with explicit thresholds, expiry-close policy, outcome persistence, and strategy-artifact backtesting with costs/slippage.
Phase 3 | Supervised | Learning | Regime computation, supervised applicability model training from stored rule/outcome history, and ranked strategy applicability serving by stock/sector/regime.

## Table 26
Task | Scope
P1 | Foundations, Schema, and FR Mapping. Create DB schema for all entities including lot sizes and signal links. Map FR1–FR15 to implementation modules and integration tests.
P2 | Market and Reference Data Ingestion. Kotak 1m OHLCV with minimum 1-month lookback. Lot-size master ingestion with effective dating. Data-quality checks and freshness monitors.
P3 | News and Announcement Ingestion. NewsAPI primary and Moneycontrol adapter. NSE announcements feed. Source ID normalisation and symbol mapping.
P4 | Signal and Screening Engine. Weighted swing+volume S/R. Technical pattern detection (breakout / reversal / consolidation / volume spike). Sentiment and sector impact fusion.
P5 | Strategy Artifact and Recommendation Engine. Versioned free-text strategy artifacts. Recommendation generation with guardrails. Mandatory recommendation_signal_links persistence.
P6 | Lifecycle Monitor and Expiry Close. Per-lot P&L using effective lot sizes. Configurable thresholds (defaults: +₹20,000 close-profit / −₹30,000 close-loss). No-rollover expiry close (T−1/same-day).
P7 | Backtesting and Metrics. Backtest from stored strategy artifacts. Cost/slippage-aware evaluation and performance reporting (win rate, average P&L, signal accuracy).
P8 | Regime Model and Supervised Applicability Learning. Implement regime computation (trend | volatility). Train and serve strategy applicability model by stock/sector/regime.
P9 | Delivery and Query Interfaces. Telegram notifications. History/query APIs for strategies, recommendations, signals, and outcomes.
P10 | Quality, Security, and Release. Integration tests for FR1–FR15. Replay tests, observability dashboards, incident runbook, and deployment checklist.

## Table 27
Task | Depends On | Notes
P1 | — | Foundation — all others block on P1
P2 | P1 | Market data and lot-size master
P3 | P1 | News/announcements ingestion (parallel with P2)
P4 | P2, P3 | Signals require ingested data from both P2 and P3
P5 | P1, P4 | Recommendations need schema (P1) and signals (P4)
P6 | P2, P5 | Monitor needs lot sizes (P2) and open recs (P5)
P7 | P5, P6 | Backtest needs strategy artifacts (P5) and outcomes (P6)
P8 | P6, P7 | Learning needs outcome labels (P6) and backtest history (P7)
P9 | P5 | Delivery needs recommendations (P5) at minimum
P10 | P7, P8, P9 | Final release gates all end-state tasks

## Table 28
Step | Task
1 | P1 — Foundations, Schema, FR Mapping
2 | P2 — Market and Reference Data
3 | P3 — News and Announcement Ingestion
4 | P4 — Signal and Screening Engine
5 | P5 — Strategy Artifact and Recommendation
6 | P6 — Lifecycle Monitor and Expiry Close
7 | P9 — Delivery and Query Interfaces
8 | P7 — Backtesting and Metrics
9 | P8 — Regime and Supervised Learning
10 | P10 — Quality, Security, and Release

## Table 29
Risk | Mitigation
Single-provider dependence (Kotak-only) can cause feed interruptions. | Cache/retry/backoff, stale-feed circuit breaker, global kill switch, and fallback to “no recommendation”.
News-source inconsistency and symbol-mapping noise. | Source-priority policy, source ID normalisation, and deduplication layer.
Free-text strategy quality variance producing noisy artifacts. | Artifact review/status workflow before production use; optional tagger for searchable metadata.
Early label sparsity in first weeks may reduce supervised model quality. | Start with simple supervised baselines and strict offline acceptance thresholds before production deployment.

## Table 30
Item | Question / Decision Required
Brokerage model | Which brokerage rate and structure (flat fee vs. percentage) should be assumed? Based on Kotak Neo’s active plan?
Statutory charges | Should STT, exchange transaction charges, SEBI turnover fee, GST, and stamp duty be included? At what rates?
Slippage model | Fixed tick slippage per trade, or a percentage-of-price model? Should it vary by stock liquidity tier?
Configurability | Should cost/slippage assumptions be configurable per backtest run, or fixed in the engine?

## Table 31
Item | Question / Decision Required
Minimum training set | What is the minimum number of labeled outcome records required before the first training run can execute?
Retraining schedule | Is retraining triggered on a fixed schedule (weekly/monthly), on a new-outcome count threshold, or manually?
Offline acceptance threshold | What evaluation metric (e.g. accuracy, AUC, Brier score) and minimum threshold must a new model version achieve on a held-out set before it is promoted to production?
Model promotion policy | Who or what approves a model version for production deployment — automated gate, manual review, or both?
Rollback policy | If production applicability scores degrade after a new model version is deployed, what triggers a rollback and how is the previous version restored?