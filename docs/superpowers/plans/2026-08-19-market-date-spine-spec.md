# Market-Date Spine — Spec

Audit source: 2026-08-19 pipeline/paper-trading review (artifact "Market-Date Spine",
https://claude.ai/code/artifact/9db2590e-c96a-4018-94ce-5c21d445ef29). Findings F1–F8 referenced below.

## Problem

Every metric, exit, and comparison in stock-trader is keyed to `collected_at` — the wall
clock of manual pipeline runs (5 run-days since April) — instead of market dates. As a result:

- **F1** Velocity compares against "24h-ago" snapshots that don't exist → composite score 0.
- **F2** Technicals (RSI-14, MA-50, Bollinger) computed on ≤11 snapshots per ticker, ever.
  `YFinanceCollector.collect_historical_prices()` exists (yfinance_collector.py:169) but is never called.
- **F3** Paper-trade stops/targets evaluated only at run time: a −10% stop exited at −42.3% after 89 days.
- **F4** `paper_trades.signal_id` NULL on all rows; `signals.outcome_*` written by no code path;
  backtester uses a private data path. No learning loop.
- **F5** Dedup key is (ticker, exact timestamp) → 11 of 28 trades are duplicates; a 0-share trade exists.
- **F6** config.yaml thresholds neutered (min_conviction 15, insider cluster 1/$10k).
- **F7** Runs take 5–6 min on sequential per-ticker API calls.
- **F8** No single-instance lock (two concurrent runs on 2026-08-19), no cadence ledger.

## Requirements

- **R1** New canonical table `price_bars(ticker, date, open, high, low, close, volume, source)`,
  PK (ticker, date), filled from yfinance daily OHLCV, gap-backfilled on every pipeline run.
- **R2** Technical analysis reads close series from `price_bars`, never from `prices` snapshots.
- **R3** A pure bar-walking exit engine (`src/trading/engine.py`): per daily bar in date order —
  gap-open through stop/target fills at the open; intrabar stop fills at stop price; intrabar target
  at target price; stop checked before target when both hit; calendar `hold_days` exit at close.
  Entry-day bar is skipped (intraday sequencing unknown).
- **R4** Paper trading replays bars through the engine on every run (positions carry
  `last_evaluated_date`), so exits approximate real resting orders regardless of run cadence.
- **R5** Paper-trade hygiene: at most one open position per ticker; reject 0-share trades;
  `signal_id` linked on every trade; existing duplicates voided (status `void_duplicate`,
  originals preserved — never deleted); performance stats exclude voided rows.
- **R6** The backtester uses the same engine and `price_bars` (no private RSI / price path for
  trade simulation), so backtest and paper book are the same experiment over different dates.
- **R7** Signal outcomes backfilled from bars: forward returns at +5/+10/+30 trading days
  (`fwd_return_5d/10d/30d`; `outcome_price/outcome_date/outcome_pct` = the 10-day point),
  and a per-trigger-type edge report surfaced in the dashboard.
- **R8** Velocity is date-normalized (two most recent distinct observation dates, per-day rate)
  and flagged stale when the observation gap exceeds 3 days.
- **R9** Single-instance lock around the pipeline; a `pipeline_runs` ledger records every run.
- **R10** Thresholds restored to honest defaults (min_conviction 40; insider cluster ≥2 / ≥$100k)
  in config.example.yaml, with instructions applied to the live gitignored config.
- **R11** A one-time revalidation utility re-closes the 20 historical closed trades against real
  bars and reports the deltas (acceptance evidence for R3/R4).
- **R12** Daily scheduled run (Windows Task Scheduler registration script).

## Non-goals

- No live/broker trading. No new data vendors. No rewrite of collectors, reporters, or the
  238-test suite (extend only). No re-weighting of conviction yet — that waits for ~50 outcomes
  per trigger type (Phase 4 of the audit, out of scope here).
