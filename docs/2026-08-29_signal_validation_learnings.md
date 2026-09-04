# Signal Validation — Findings and Learnings

**Period:** 2026-08-23 → 2026-08-29
**Scope:** Data-integrity audit of the signal pipeline, correction of the edge table, and one live $200 execution test through the Robinhood agentic account.
**Status:** Position closed. Pipeline fixes committed. No validated edge found.

---

## 1. Summary

The pipeline had five defects that, together, manufactured an apparent edge that does not exist. All five are fixed and covered by tests. After the fixes, **no trigger in the system has a demonstrated edge** — the momentum trigger is measurably negative, and the insider trigger's sample collapsed to n=2.

A live $200 trade (REFI) was run to validate the execution path end to end. The execution machinery worked exactly as designed. The trade itself was closed flat-to-slightly-down, as expected for a position with no edge behind it.

**The pipeline is now trustworthy. The signals are not yet.**

---

## 2. Defects found and fixed

### 2.1 Split contamination in forward returns
`src/analysis/outcomes.py` used `price_at_signal` (captured live, unadjusted) as the baseline against `price_bars` closes (retroactively split-adjusted). Mixing adjustment bases fabricates returns.

| Ticker | price_at_signal | bar close, same day | recorded 5d return |
|---|---|---|---|
| SOXS 2026-05-22 | $7.67 | $1,146.15 | **+706.78%** |
| SPCX 2026-05-22 | $22.30 | — | **+593.24%** |

Those two rows alone lifted `velocity_spike`'s 5-day mean from +5.33% to +34.76%.

**Fix:** baseline is always the signal-day bar close, so numerator and denominator share one adjustment basis. Added `_split_boundary()`, which rejects any horizon whose window crosses a >2× or <0.5× single-session ratio and leaves the outcome NULL rather than writing a fabricated number.

### 2.2 Insider row duplication
`insiders` had no UNIQUE constraint and used a plain `INSERT`. OpenInsider's cluster / CEO-CFO / purchase views overlap, so each trade landed several times per run and again on every later run.

**3,400 rows → 753 distinct (78% duplicated).**

Because the cluster trigger counted rows, a single CEO purchase read as a seven-buyer cluster. Intel's "7 insiders bought $69,999,895" was one $10.0M purchase counted seven times.

**Fix:** `INSERT OR IGNORE` plus a unique index on the Form 4 natural key. Verified live — a subsequent run offered 204 rows and stored 4.

### 2.3 Same-day signal duplication
`signals` had `UNIQUE(ticker, created_at)`, but `created_at` carries microseconds, so every pipeline run in a day inserted a fresh row for the same ticker. 121 rows → 96.

**Fix:** unique index on `(ticker, signal_type, date(created_at))`.

### 2.4 Grain mixing — roll-ups counted against their own components
OpenInsider's cluster view returns **aggregate** rows summing several Form 4 filings. Those sat in the same table as the individual filings they summarise, and the trigger counted both.

**352 of 753 rows (47%) are roll-ups.**

Reconciliation was attempted and **does not work** — only 4 of 352 roll-ups reconcile exactly against their components, because the individual views only scrape officers above a dollar floor and never captured the roll-up's other buyers.

**Fix:** grain *separation*, not reconciliation (`src/analysis/insider_grain.py`). Totals come from exactly one grain, named in `verdict.basis`, never a cross-grain sum. Cluster status is established by either ≥2 distinct named Form 4 buyers or the presence of a roll-up.

### 2.5 Channel blindness — offering participation read as conviction
Form 4 code `P` covers open-market buys, registered-offering participation, and exercises at strike alike. The collector also flattened OpenInsider's qualified string (`"P - Purchase+OE"`) to bare `'P'` before storage, destroying the only direct evidence.

Intel's CEO bought 105,263 shares at exactly $95.00 **inside a $20B upsized offering** (210.5M new shares). The pipeline read it as a $10M conviction buy.

**Fix:** preserve the qualified code in `acquisition_code`; derive `acquisition_channel` from a bar-range test — an open-market fill must print inside that session's low–high range. Offerings price at a discount, so *below the low* is off-market; *above the high* is a data anomaly and gets its own label.

Validated against known cases:

| Ticker | Date | Paid | Session range | Verdict |
|---|---|---|---|---|
| INTC | 2026-08-11 | $95.00 | 95.35–98.35 | off_market (the $20B offering) |
| MSTR | 2026-03-19 | $99.62 | 132.76–139.78 | off_market |
| FEMY ×2 | 2026-08-07 | $3.20 | 2.29–3.14 | price_anomaly |
| KEEL / CC / OPEN | — | — | — | open_market, all correct |

**After expanding bar coverage from 23 to 396 of 405 Form 4 rows: 15.6% of all Form 4 "purchases" were not priced by the open market** (9.4% off-market, 6.2% anomaly).

---

## 3. The corrected edge table

| Trigger | n | 5d median | 30d median | 30d win |
|---|---|---|---|---|
| velocity_spike | 43 | +4.06% | **−7.50%** | 35% |
| insider_cluster | 7 → **2** after filtering | — | — | — |
| news_sentiment_bullish | 5 | +1.11% | +1.26% | 60% |

Benchmark in-sample: SPY 5d +1.73% / 30d +0.23%.

**velocity_spike runs −7.73pp of 30-day alpha.** It is not a neutral signal; it is a measurably bad one. Every one of its entries fires *after* a 3–15% move has already happened.

**insider_cluster's apparent edge was manufactured by the duplicate rows.** Re-running the historical signals through grain and channel filtering:

| Ticker | 30d | Verdict |
|---|---|---|
| GO | +2.49% | still fires — CEO + genuine roll-up |
| NKE | +1.17% | still fires — CEO + genuine roll-up |
| CIA | +2.35% | dropped — 4 buys, all one person |
| SOFI ×2 | +17.38%, +13.51% | dropped — all one person |
| AMC | **+26.49%** | dropped — one buy, counted twice |

Sample 6 → 2. **Every large winner dropped out.** The survivors' 30-day median is +1.83% against SPY's +0.23% — indistinguishable from noise at n=2.

**Independence is the binding constraint.** 45 of 54 outcomes share a single observation date (2026-05-22). Effective independent sample ≈ 4 dates, not 54 rows.

---

## 4. Structural limitations discovered

**4.1 Insider clusters are invisible without Reddit chatter.** `generate_signals()` iterates `velocity_data.keys()`, so a cluster on a ticker nobody posts about can never produce a signal. On 2026-08-24 there were **44 live qualifying clusters**; almost none could signal. This structurally subordinates the only non-negative trigger to social mentions.

**4.2 No OCO / bracket orders in the Robinhood MCP.** A stop and a take-profit cannot coexist on the same shares — the first order placed claims all of them (`shares_held_for_sells: 18`, `shares_available_for_sells: 0`). Exits must be single-order, and changing the exit plan starts with a cancel. The engine's paper bracket cannot be reproduced live.

**4.3 Bar coverage gates the channel test.** With only signal+trade tickers in the spine, the test reached 23 of 401 Form 4 rows. Widening the backfill universe to include insider tickers (160 → 452) raised it to 396 of 405. Rows without a bar stay `unverified` and cannot be checked — BABA's "$15.3M cluster" was priced at $14.24 against a ~$119 ADR (the Hong Kong listing) and was only caught by eye.

**4.4 SQLite cannot be written over the device mount.** Commits fail with `disk I/O error` and leave a stale rollback journal. Do database work in the container and commit the file back.

---

## 5. The live execution test

| | |
|---|---|
| Instrument | REFI (Chicago Atlantic Real Estate Finance) |
| Selection basis | Only candidate clearing all four filters: 2 named open-market Form 4 buyers, corroborated by company press release (~54,000 sh / ~$673,000 by officers and directors), lowest stop-out probability in the set (14% vs 76–85% for the aggressive tier), no earnings in window |
| Entry | 18 sh @ **$10.85**, 2026-08-25 09:30:00 ET, $195.30, $0 fees |
| Stop | $9.77 → revised to $9.55 |
| Exit | Limit sell @ $10.55, placed 2026-08-29 |
| Result | Approximately **−$3** |

**What worked:** signal → grain-verified cluster → review → order → fill → automated stop placement via scheduled task → stop revision → exit. Every step executed and is auditable. The scheduled task correctly derived the stop from the *actual* fill price rather than the estimate.

**What the trade proved:** the execution path. Nothing about signal quality.

---

## 6. Analytical conclusions that generalise

**6.1 The ±20% / −10% bracket is EV-neutral.** Gambler's ruin: P(take-profit first) = 10/(10+20) = **33.3%**, EV = (⅓)(+20%) + (⅔)(−10%) = **0.00%** before costs. Volatility changes only how fast a position resolves, never its expectation. The bracket contributes nothing; all expectancy must come from the signal.

**6.2 The bracket is mis-calibrated for low-volatility instruments.** It was tuned on high-vol momentum names. On REFI (19.7% annualised, 1.24%/day):

| Barrier | Distance | P(touch in 30d) |
|---|---|---|
| −10% stop | 8.1σ | 14.0% |
| +20% target | 16.2σ | **0.3%** |

A +20% target on a 20%-vol name is decoration. **Express barriers in daily sigma, not percent.**

**6.3 Stop distance should be measured against structural levels, not round percentages.** The original $9.77 stop sat 8 cents above the 52-week low of $9.69 — a level tested four weeks earlier. Widening to $9.55 (below the low) *lowered* expected loss despite raising the loss-if-hit:

| Stop | P(hit/30d) | Loss if hit | Expected loss |
|---|---|---|---|
| $9.77 | 20.5% | −$19.44 | −$3.99 |
| $9.55 | 11.6% | −$23.40 | −$2.72 |

**6.4 A dividend is not added return over a short window.** On the ex-date you receive the cash *and* the share price drops by approximately the same amount. Net effect that day is zero. A high yield is only real return if the price holds up across quarters. This was initially mis-stated as "+4.3%" in the REFI case and is corrected here.

**6.5 With no edge, expected value is approximately zero minus costs.** Simulated 60 trading days from entry, zero drift assumed: mean −$2.08, median −$6.81, 39% chance of profit, 5th/95th percentile −$14.94 / +$28.19. Not a guaranteed loss — a coin flip with a truncated left tail and a small drag.

---

## 7. What to try differently

1. **Decouple insider clusters from the velocity universe.** Let `generate_signals` iterate the union of velocity tickers and tickers with live clusters. Until then the only non-negative trigger is largely unreachable.
2. **Stop trading `velocity_spike` entries.** −7.73pp of measured 30-day alpha across 43 samples is the strongest single result in this audit, and it is negative. If the trigger is kept, test it as a *short* or a fade rather than a long.
3. **Get to a real sample before risking capital again.** The binding constraint is independent observation dates, not row count. At one pipeline run per weekday, a usable per-trigger sample is months away. Paper-only until then.
4. **Size barriers to the instrument.** Set take-profit and stop as multiples of realised daily sigma, with a floor at the nearest structural level, rather than fixed ±20/−10.
5. **Reconcile roll-up aggregates against components** where components exist, and add an acquisition-code field wherever OpenInsider supplies a qualified string, so the channel test does not depend solely on bar coverage.
6. **Add a same-day-extension filter.** Every `combined` signal on 2026-08-21 fired on a name that had already moved 3–15% that session. Entry after a completed move is the mechanism behind the negative alpha.

---

## 8. Open items

- `acquisition_code` cannot be backfilled — the collector discarded it before storage. Only rows collected after 2026-08-23 carry one.
- Distinct-buyer counting uses name+title; a Form 4 row with a blank name collapses into another blank one. Conservative (under-fires), but a known limitation.
- The bar-range channel test cannot detect a same-day offering priced *inside* the range.
- `min_insiders=2` with roll-ups as an alternate route means a two-person and a twenty-person cluster look identical.
- The stop placed by the 2026-08-25 scheduled task was created ~10.5 hours after the trigger time. Outcome was correct; cause unexplained.
- `paper_trades.pnl` is a dead column — never written, never read. All code uses `profit_loss`. Annotated, not migrated.

---

## 9. Files changed

| Path | Change |
|---|---|
| `src/analysis/outcomes.py` | v1.1.0 — baseline fix, split-boundary guard |
| `src/analysis/insider_grain.py` | **new** — grain separation, channel classification, cluster evaluation |
| `src/database/models.py` | unique indexes, `INSERT OR IGNORE`, three insider columns, bar universe widened to insider tickers |
| `src/collectors/openinsider.py` | preserve qualified acquisition code |
| `src/signals/generator.py` | grain-aware cluster trigger and notes; verdict computed once |
| `tests/test_insider_grain.py` | **new** — 19 tests |
| `tests/test_signals.py` | fixtures updated to the corrected contract; 2 regression tests pinning the Intel case |
| `utils/repair_outcomes_and_dupes.py` | **new** — one-time dedupe and outcome clear |
| `utils/backfill_acquisition_metadata.py` | **new** — grain and channel backfill |

**Tests: 230 passed, 1 skipped** (was 195 before this work).

Backups: `archive/patch_backup_20260823_043810/`, `archive/patch_backup_20260823_grain/`
Removed rows archived verbatim: `archive/repair_20260823_045757/`
