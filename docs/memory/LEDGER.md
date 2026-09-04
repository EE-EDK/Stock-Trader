# Project Memory — Ledger

> **Generated file. Do not edit.** Written by `docs/memory/memory.py`.
> Source of truth is `ledger.jsonl`. Add entries with `python docs/memory/memory.py add ...`.

**37 live entries · 6 superseded · last updated 2026-09-04**

## Read this first

**Do not repeat these:**
- `#1` velocity_spike entries have negative 30-day alpha — do not trade them long
- `#2` Roll-up/component reconciliation does not work — use grain separation instead
- `#3` The +20%/-10% bracket is EV-neutral and mis-calibrated for low-volatility names
- `#4` SQLite cannot be written over the device mount — work in the container and commit the file
- `#5` yfinance transport is blocked in the cloud container — use plain-TLS urllib for bars
- `#35` Editing this repo's .py files with plain Python text-mode read/write silently flattens CRLF to LF

**Unresolved:**
- `#11` Sample independence is the binding constraint — 45 of 54 outcomes share one date
- `#20` acquisition_code cannot be backfilled for historical rows

---

## Open questions

*Unresolved. Do not assume an answer.*

#### `#20` acquisition_code cannot be backfilled for historical rows

*2026-08-29 · VERIFIED · open* · `data-integrity` `insiders` `limitation`

The collector flattened OpenInsider's qualified trade-type string to bare 'P' and discarded the original before it ever reached the database. Only rows collected after 2026-08-23 carry a code. Historical rows are classified on the bar-range test alone, which cannot detect a same-day offering priced inside the session range.

**Evidence:** src/collectors/openinsider.py line ~257 before the fix.

#### `#11` Sample independence is the binding constraint — 45 of 54 outcomes share one date

*2026-08-23 · VERIFIED · open* · `edge` `methodology` `blocker`

The edge table looks like n=54 but 45 outcomes come from a single observation date (2026-05-22) and there are only 4 distinct dates in total. Cross-sectionally correlated observations are not independent samples; effective n is closer to 4. No per-trigger conclusion drawn from this table should be treated as significant. At one pipeline run per weekday, a usable sample is months away. This is the single strongest argument for staying on paper.

**Evidence:** SELECT date(created_at), COUNT(*) FROM signals WHERE outcome_pct IS NOT NULL GROUP BY 1.

*measured at n=4 · **re-test when:** >=20 independent observation dates in the outcomes table*

---

## What does not work

*Tried and failed, or measured and found harmful. Do not repeat these.*

#### `#35` Editing this repo's .py files with plain Python text-mode read/write silently flattens CRLF to LF

*2026-09-02 · VERIFIED · validated* · `tooling` `process` `device-bridge`

No .gitattributes in this repo. src/ and main.py are Windows-authored CRLF throughout; tests/ files are LF-only. A naive open(path,encoding='utf-8').read() / open(path,'w',encoding='utf-8').write(text) round-trip on a CRLF file converts EVERY line ending to LF (Python's universal-newlines translates on read, writes platform-default -- LF on this Linux-side device_bash -- on write), producing a diff where every line appears changed even when only a few lines were touched. Caught immediately (checked b'\r\n' counts before vs after) and fixed by re-converting b'\n' -> b'\r\n' post-edit on the 5 affected files (openinsider.py, models.py, insider_grain.py, generator.py, main.py) before verifying syntax and committing. Do instead: before any Edit/sed/python-text-write on a file in this repo, check its line-ending convention first (python3 -c "print(open(p,'rb').read().count(b'\r\n'))") and restore it after, OR do binary-safe find/replace (open in 'rb'/'wb', operate on bytes) so the file's existing convention is never touched.

**Evidence:** src/collectors/openinsider.py, src/database/models.py, src/analysis/insider_grain.py, src/signals/generator.py, main.py -- all CRLF before and after this session's edits; config/config.yaml also CRLF, fixed via binary-safe replace on the first attempt

#### `#5` yfinance transport is blocked in the cloud container — use plain-TLS urllib for bars

*2026-08-23 · VERIFIED · validated* · `tooling` `environment` `collectors`

yfinance 1.6.0 drives HTTP through curl_cffi with browser TLS impersonation. The container's egress proxy resets every such connection ('curl: (35) Recv failure: Connection reset by peer') — the collector scored 0/452 tickers. Plain-TLS urllib to the identical Yahoo chart endpoint (query1.finance.yahoo.com/v8/finance/chart/SYMBOL) works normally. Workaround: a transport-only shim exposing collect_historical_prices(), driven by the project's own backfill_price_bars() so the gap logic and write path are unchanged. This is a CONTAINER-ONLY issue; yfinance works fine in the Windows venv.

**Evidence:** 0/452 via yfinance vs 446/452 via urllib shim, same session, 2026-08-23. Spot-checked against Robinhood: CC $15.97, KEEL $3.32, INTC $90.07 all exact.

**ENFORCED** — blocks: `env:container`, `tool:yfinance`

#### `#4` SQLite cannot be written over the device mount — work in the container and commit the file

*2026-08-23 · VERIFIED · validated* · `tooling` `environment` `do-not-repeat`

Writing to data/sentiment.db through the mounted device folder fails with 'sqlite3.OperationalError: disk I/O error' at commit and leaves a stale rollback journal behind, which device_bash cannot delete. The transaction rolls back cleanly (integrity_check ok) but nothing is written. Correct workflow: stage the DB into the container, do all SQLite work there, commit the finished file back via device_commit_files. Verify by sha256 on both sides.

**Evidence:** Reproduced 2026-08-23 running utils/repair_outcomes_and_dupes.py --apply over the mount.

**ENFORCED** — blocks: `env:device_mount`, `tool:sqlite_write`

#### `#3` The +20%/-10% bracket is EV-neutral and mis-calibrated for low-volatility names

*2026-08-23 · VERIFIED · validated* · `exits` `sizing` `do-not-repeat`

Gambler's ruin on a driftless asset: P(take-profit first) = 10/(10+20) = 33.3%, so EV = (1/3)(+20%) + (2/3)(-10%) = 0.00% before costs. The bracket contributes nothing; all expectancy must come from the signal. Worse, it was tuned on high-vol momentum names. On a 20%-annualised-vol instrument the -10% stop is 8.1 sigma away (14% chance of touch in 30d) and the +20% target is 16.2 sigma away (0.3% chance) — the take-profit is decoration. Express barriers in multiples of realised daily sigma, with a floor at the nearest structural level, not as fixed percentages.

**Evidence:** First-passage probabilities computed from 20-day realised vol; verified against REFI (19.7% ann., 1.24%/day).

***re-test when:** barriers re-expressed as multiples of realised daily sigma*

**ENFORCED** — blocks: `config:bracket_20_10`

#### `#2` Roll-up/component reconciliation does not work — use grain separation instead

*2026-08-23 · VERIFIED · validated* · `insiders` `architecture` `do-not-repeat`

Attempted to reconcile OpenInsider cluster roll-up rows against the individual Form 4 rows they summarise. Only 4 of 352 roll-ups reconcile exactly; 343 are unexplainable. Root cause: the individual views (collect_ceo_cfo_buys, collect_insider_purchases) only scrape officers above a dollar floor, so the roll-up's other buyers were never collected and there is no complete component set to reconcile against. Do not re-attempt this. The working approach is grain SEPARATION — totals come from exactly one grain, never a cross-grain sum.

**Evidence:** Measured across the full insiders table 2026-08-23. See src/analysis/insider_grain.py module docstring.

*measured at n=352 · **re-test when:** OpenInsider exposes a buyer-count column on the cluster view*

**ENFORCED** — blocks: `approach:rollup_reconciliation`

#### `#1` velocity_spike entries have negative 30-day alpha — do not trade them long

*2026-08-23 · VERIFIED · validated* · `edge` `velocity` `do-not-repeat`

After removing split-contaminated outcomes and deduplicating, velocity_spike shows a 30-day median of -7.50% against SPY's +0.23% over the same window: -7.73pp of alpha across n=43. The 5-day median is mildly positive (+4.06% vs SPY +1.73%), so the signal front-runs nothing and mean-reverts hard. Mechanism: every 'combined' signal on 2026-08-21 fired on a name that had ALREADY moved 3-15% that same session (HOOD +13.7%, SLS +15.4%, MSTR +6.1%). Entry is after the move is complete. If this trigger is kept, test it as a fade or short, not a long.

**Evidence:** Corrected edge table, docs/2026-08-29_signal_validation_learnings.md §3. n=43 deduped, split-guarded.

*measured at n=43 · **re-test when:** n>=100 velocity_spike outcomes across >=20 independent observation dates*

**ENFORCED** — blocks: `trigger:velocity_spike`, `action:buy`

---

## Validated findings

*Measured results with evidence attached.*

#### `#38` Raising max_open_positions to 40 (#34) mostly added velocity_spike exposure, not insider_cluster/news_sentiment_bullish

*2026-09-03 · VERIFIED · validated* · `paper-trading` `velocity` `capacity` `review`

Reviewed 2026-09-03 at user request to rethink next action. Paper book is now full (40/40 open slots, the new cap from #34). Overall closed-trade P&L across all 33 closed paper trades: 33.3% win rate, avg return_pct -0.98%, total pnl -394.36 dollars (17 stop_loss exits avg -10.09%, 7 take_profit avg +20.0%, 9 time_limit avg -0.09%). By dominant signal_types on CLOSED trades: velocity_spike-only 19 trades avg -2.09% (58% of all closed volume); insider_cluster-only 7 trades avg +3.37%; news_sentiment_bullish-only 4 trades avg +3.46%. create_paper_trade() admission (src/trading/paper_trading.py) gates only on conviction, capacity, and one-open-per-ticker -- it is blind to which trigger produced the signal. Because velocity_spike fires far more often than insider_cluster or news_sentiment_bullish (108 vs 15 vs 9 signals generated all-time), it naturally dominates admission once conviction clears the floor. This is NOT a code bug: #29 already established paper trading is deliberately not gated by guard.py so it can keep re-testing entry #1's velocity_spike finding out-of-sample. And it IS re-testing it: the fresh -2.09% avg / 33.3%-win-rate realized paper result on new calendar dates (8/19 through 9/2) points the same direction as #1's original -7.73pp/n=43 finding from 2026-08-23, which is reassuring methodologically -- but it also means the #34 capacity increase, justified purely by slot-count vs signal-volume math, ended up buying mostly more confirmation of an already-known-bad trigger rather than more data on the two triggers actually gating decision #19 (insider_cluster at 5/20 independent dates, news_sentiment_bullish dormant since 2026-08-19). Flagging as a live decision point rather than fixing unilaterally: changing admission to bias slots toward under-sampled promising triggers touches paper_trading.py, main.py and their tests (3+ files) -- left for explicit user direction per the >=3-file pause trigger, not implemented this turn.

**Evidence:** data/sentiment.db paper_trades table, queried 2026-09-03T16:4x UTC: closed n=33, GROUP BY signal_types and exit_reason; src/trading/paper_trading.py create_paper_trade() read directly, no trigger-type gating found; entry #1 and #29 cross-referenced

#### `#29` Paper trading is intentionally NOT gated by guard.py -- it is how blocked triggers reach retest_when

*2026-09-02 · VERIFIED · validated* · `architecture` `paper-trading` `guard`

Observed 2026-08-31 scheduled run (logs/pipeline.log:4077-4084): main.py's ledger pre-flight logged '[LEDGER] 3 velocity_spike signals have a recorded failure against them: TSLA, AMZN, VOO', then src.trading.paper_trading opened paper positions in TSLA and AMZN anyway. This is NOT a bug and should not be fixed. Two-tier design (see #23, #26): guard.py hard-blocks only at the real-money chokepoint (journal.open_trade, action:live_trade). Signal generation and paper trading are advisory-only by design -- if paper trading also refused entry #1's flagged triggers, velocity_spike could never accumulate the >=20 independent observation dates its own retest_when requires, and the block would calcify permanently instead of being re-testable. Confirmed no automated code path calls place_equity_order or journal.open_trade -- grepped logs/pipeline.log for place_equity/live_trade/real, zero matches across all runs to date.

**Evidence:** logs/pipeline.log lines 4077, 4081-4082 (2026-08-31 18:37:42 run)

#### `#28` REFI trade closed: predicted near-flat exit realized almost exactly (n=1)

*2026-09-02 · VERIFIED · validated* · `execution` `calibration` `REFI`

Journal entry #1 closed against the real fill: exit order 6a936499 filled 2026-08-31T13:30:00Z (Monday open) at $10.69 (better than the $10.55 limit), entry $10.85, 18 sh, held 6 days. Realized -$2.88 / -1.47%. Compared to the prior recorded in journal.py BEFORE the outcome was known (2026-08-24, at trade open): most_likely='time-based exit near flat' -- matches. p_stop_30d=0.14 was never tested since the stop was cancelled and replaced with a manual limit exit before 30 days elapsed or any stop trigger fired. stated_edge=null -- confirmed; no edge was claimed going in and none showed up in the outcome. This is n=1, a single trade proves nothing about the pipeline's edge -- it only confirms the journal/calibration mechanism itself works end to end (prior recorded before outcome, outcome scored against prior after). Do not read this as validating or invalidating insider_cluster.

**Evidence:** live_trades id=1, broker_order_id 6a8cd230-bf1c-498a-a40c-43c205b0f3e3, exit_order_id 6a936499-0d8d-4df3-9769-097f04e22576, sentiment.db

*measured at n=1 · **re-test when:** n/a -- single-trade calibration check, not a statistical claim*

#### `#25` Findings need falsifiability metadata or they calcify into dogma

*2026-08-29 · DERIVED · validated* · `memory` `methodology`

A bare conclusion like 'velocity_spike has -7.73pp alpha' hardens into a rule nobody re-tests. Entries now carry sample_n and retest_when, so every enforced block states the sample it rests on and the condition that overturns it. #1 is enforced at n=43 and re-opens at n>=100 across >=20 independent dates. This matters most for a system whose whole job is to re-measure as the sample grows.

**Evidence:** memory.py annotate; rendered in LEDGER.md and surfaced by guard.py explain().

#### `#18` Stop placement should be set against structural levels, not round percentages

*2026-08-29 · DERIVED · validated* · `exits` `sizing`

A -10% stop on REFI landed at $9.77 — eight cents above the 52-week low of $9.69, a level tested four weeks earlier. Widening to $9.55 (below the low) LOWERED expected loss despite raising the loss-if-hit, because it removed the probability of being knocked out by an ordinary retest: 20.5% x -$19.44 = -$3.99 versus 11.6% x -$23.40 = -$2.72. Also account for the ex-dividend drop: a $0.47 dividend on a $10.69 stock mechanically moves price 4.4% toward the stop, and the stop cannot tell that is not a loss.

**Evidence:** First-passage probabilities over 30 trading days at 1.24% daily sigma.

#### `#17` A dividend is not added return over a short window — the ex-date drop offsets it

*2026-08-29 · DERIVED · validated* · `methodology` `income` `correction`

Initially framed REFI's 17.6% yield as '+4.3% per quarter' on the position. That is wrong. On the ex-date you receive the cash AND the share price drops by approximately the same amount; net effect that day is zero. A high yield is only real return if the price holds up across quarters. Correcting this materially weakened the REFI case after the position was already open — the yield was found after selection, not before it. Lesson: pull dividend and credit profile BEFORE selecting, not after.

**Evidence:** $0.47/sh on 18 sh = $8.46 cash; simultaneous price drop 18 x $0.47 = $8.46.

#### `#16` The execution path works: signal to fill to automated stop to exit, fully auditable

*2026-08-29 · VERIFIED · validated* · `execution` `robinhood`

Validated end to end: grain-verified cluster -> review_equity_order -> place_equity_order -> fill -> scheduled task read the ACTUAL fill price and derived the stop from it (not the estimate) -> stop revised on new analysis -> exit placed. Every step is recoverable from order ids and placed_agent='agentic' filtering. This half of the system is trustworthy. One unexplained detail: the scheduled task's stop was created ~10.5 hours after its trigger time; outcome was correct, cause unknown.

**Evidence:** Orders 6a8cd230 (buy), 6a8e3027 (stop @ 9.77), 6a936330 (stop @ 9.55), 6a936499 (exit).

#### `#14` Bar coverage gates the acquisition-channel test

*2026-08-24 · VERIFIED · validated* · `data-integrity` `bars` `insiders`

The channel test needs a price bar for the trade date. With only signal+trade tickers in the spine it reached 23 of 401 Form 4 rows (5.7%). Widening the bar-backfill universe to include insider tickers (160 -> 452) raised coverage to 396 of 405 and exposed 63 contaminated rows instead of 4. Rows without a bar stay 'unverified' and cannot be checked — BABA's apparent $15.3M cluster was priced at $14.24 against a ~$119 ADR (that is the Hong Kong listing) and was caught by eye, not by the classifier.

**Evidence:** get_signal_and_trade_tickers() now unions the insiders table; docstring records the 23/401 measurement.

#### `#13` The Robinhood MCP has no OCO — one exit order claims all the shares

*2026-08-24 · VERIFIED · validated* · `execution` `robinhood` `architecture`

There is no bracket/OCO order type in the tool surface. A protective stop and a take-profit limit cannot coexist on the same shares: whichever is placed first sets shares_held_for_sells to the full quantity and shares_available_for_sells to 0. Any change to the exit plan must begin with cancelling the existing order. Consequence: the paper engine's +20/-10 bracket cannot be reproduced live, and live results will diverge from backtest on exit behaviour alone.

**Evidence:** Observed directly on the REFI position: 18 shares held_for_sells with the stop open, 18 available after cancelling.

#### `#10` The insider_cluster edge was manufactured by the duplicate rows — sample collapsed 6 to 2

*2026-08-23 · VERIFIED · validated* · `edge` `insiders`

Re-running the historical insider_cluster signals through grain and channel filtering drops four of six, and EVERY large winner is among them: AMC +26.49% (one buy, counted twice), SOFI +17.38% and +13.51% (three buys, all Anthony Noto), CIA +2.35% (four buys, all Jon Stenberg). The two survivors — GO and NKE — are the only ones with genuine multi-insider cluster filings, and their 30-day median is +1.83% against SPY's +0.23%. Verified this is not retrospective data loss: every dropped ticker still has all its rows; they are one person's repeat buying that row-counting read as a cluster.

**Evidence:** docs/2026-08-29_signal_validation_learnings.md §3.

---

## Fixes applied

*Defects found and corrected, with what proved them.*

#### `#43` Sentiment collection top_n raised 20->50 and wired to config (was a dead, hardcoded-20 knob despite gui.py exposing it)

*2026-09-04 · VERIFIED · validated* · `fix` `sentiment` `config` `dead-code`

Implements the user's #41 'widen partially' decision. main.py line ~272: 'top_tickers = list(tracked_tickers)[:20]' was a hardcoded literal -- it never read config['collection']['alphavantage']['top_n'], even though gui.py line 396 exposes exactly that field as a user-adjustable 'Top N Tickers' control (range 1-100). That made the GUI control a no-op: changing it in config.json/config.yaml did nothing. Fixed by reading config.get('collection', {}).get('alphavantage', {}).get('top_n', 20) into a new alpha_top_n local, defaulting to the old hardcoded value of 20 if the key is ever absent (config validation currently guarantees it is present). config/config.yaml collection.alphavantage.top_n raised 20 -> 50 with an inline comment. This widens both collect_alphavantage() and collect_vader() (both take top_tickers) from the top 20 to the top 50 velocity-tracked tickers by 7-day mention count -- roughly 2.5x the sentiment API/scrape volume, not the ~8x a full widen to 163 tickers would have cost. Insider-only tickers remain excluded (tracked_tickers is derived from mentions/velocity, not from OpenInsider) -- the user was told this tradeoff explicitly before choosing this option over the other two. Both files are Windows CRLF; edited via binary-safe rb/wb replace, CRLF count verified before/after (main.py 812->813, +1 line as expected; config.yaml 77->77, same line count). ast.parse(main.py) and yaml.safe_load(config.yaml) both confirmed valid post-edit. Full test suite re-run: 326 passed, 1 pre-existing skip (unchanged from before this edit) -- no test exists that pins this specific line, none needed given the change is a 2-line, backward-compatible-default config lookup.

**Evidence:** main.py lines 271-273; config/config.yaml collection.alphavantage.top_n=50; gui.py:396 confirms the previously-dead config knob; pytest tests/ -q -> 326 passed, 1 skipped

#### `#36` Insider clusters can now signal without mention chatter -- generate_signals() iterates the union of tickers

*2026-09-02 · VERIFIED · validated* · `architecture` `insiders` `fix`

Correction of #31: that entry's detail text was garbled by an accidental shell backtick-substitution when it was recorded (the word 'prices' between backticks was stripped to blank by bash). Same fix, clean text. src/signals/generator.py: changed the main loop from iterating velocity_data.keys() only to iterating the union of velocity_data.keys() and insider_data.keys(), with vel/price/tech/sentiment all defaulting via .get(ticker, {}) instead of direct indexing (the old code would KeyError on velocity_data[ticker] for an insider-only ticker). Necessary but NOT sufficient on its own: insider_cluster contributes a flat 25 conviction points against the production 40-point floor (config/config.yaml thresholds.minimum_conviction), so a companion fix was required in main.py -- technical_data and sentiment_data were ALSO scoped to velocity_data.keys() only, so a cluster-only ticker had no second trigger available to clear 40. Widened both to the same union (technical_data is DB-only / zero API cost per its own docstring; sentiment_data merge just re-keys already-fetched dicts, also free). Also added a price fallback (Database.get_latest_bar_closes, reading the free price_bars table) for tickers the Finnhub-backed prices table does not cover, and reused it for paper-trade entry pricing too (that was a second, separate Finnhub-only lookup that would have silently dropped every insider-only paper trade candidate even after signal generation was fixed). Verified against the LIVE database, read-only, 2026-09-02: union was 160 tickers (100 velocity + 60 insider-only after dedup), and PRTS fired (insider_cluster + technical_breakout, conviction 59) -- a signal that was structurally impossible before this fix. 15 new tests added across test_signals.py and test_database_models.py; full suite 327 passed, 1 pre-existing skip.

**Evidence:** src/signals/generator.py, main.py Step 2b/3, src/database/models.py get_latest_bar_closes; live read-only run 2026-09-02 produced PRTS conviction 59

#### `#33` ownership_change_pct was stored as a raw share count, not a percent -- column-detection substring collision

*2026-09-02 · VERIFIED · validated* · `insiders` `data-quality` `fix`

Discovered while investigating #21 (not previously known/logged). _detect_column_map's pattern list for ownership_change_pct included the bare word 'owned', which is a substring of OpenInsider's 'Owned' header (raw shares owned) that sits ONE COLUMN BEFORE the real 'DeltaOwn' (percent) header on every OpenInsider table -- cluster AND non-cluster alike. First-match-wins column detection bound ownership_change_pct to the wrong column. Confirmed against the live DB before fixing: stored values included 3225.0, 112416.0, 27505335.0 -- physically impossible as percentages. Impact was LATENT, not live: grepped every consumer, ownership_change_pct is stored and read back (models.py/queries.py) but never used by any signal, filter, or threshold, and is not rendered in any report/dashboard template -- zero signals or trades were affected. Fix: removed the bare 'owned' pattern, kept the more specific 'delta-own'/'own change'/'ownchange'/'%own' variants. Verified live 2026-09-02: LILA now parses to 12.0 (was 36086707.0).

**Evidence:** src/collectors/openinsider.py _HEADER_PATTERNS; live DB rows before fix (ticker RHLD=3225.0, OPFI=27505335.0); grep confirmed zero downstream consumers

#### `#32` Cluster size is no longer blind -- OpenInsider's own 'Ins' column is now captured and used

*2026-09-02 · VERIFIED · validated* · `insiders` `fix` `precision`

Checked live against openinsider.com 2026-09-02 (not assumed): the latest-cluster-buys table header is ['X','Filing Date','Trade Date','Ticker','Company Name','Industry','Ins','Trade Type','Price','Qty','Owned','DeltaOwn','Value',...] -- 'Ins' is the real buyer count (live sample: LILA=5, UAMY=3, GO=2). The collector never captured it. Added exact-text column detection (not substring -- 'ins' is also a substring of 'insider name' on the non-cluster tables) and store it as insiders.insider_count (new column, idempotent migration via Database._ensure_column, live sentiment.db migrated 2026-09-02, 861 existing rows unaffected -- NULL for all of them, they predate this fix and cannot be backfilled without re-scraping). evaluate_cluster() now uses it: rollup buyer_count is the real count when available (ClusterVerdict.buyer_count_exact=True, note drops the '+' hedge), and the min_insiders fires-gate applies to rollups too (a hypothetical Ins=1 rollup would not fire) rather than firing on bare roll-up presence. Legacy rows (insider_count=NULL) keep the OLD behavior exactly -- presence-based firing, buyer_count floored at min_insiders -- so no historical verdict is silently reclassified. 5 new tests in test_insider_grain.py, 2 in test_collectors_detailed.py (live-fixture based, not network-dependent).

**Evidence:** src/collectors/openinsider.py (_detect_column_map, _scrape_table), src/analysis/insider_grain.py (evaluate_cluster); live fetch 2026-09-02 http://openinsider.com/latest-cluster-buys

#### `#27` Memory system covered by 17 tests, including two regressions from its own build

*2026-08-31 · VERIFIED · validated* · `memory` `testing`

tests/test_memory.py pins the three invariants: (1) ledger.jsonl is strictly append-only - supersede and annotate never rewrite an existing line, asserted byte-for-byte; (2) guard matching is a conjunction - the regression test is insider_cluster, which the first any-match implementation wrongly blocked because it shared action:buy with the velocity entry; (3) a blocked trade refuses without an override reason and records it when given. Also pins _next_id against annotation rows carrying id=None, which crashed it during the build.

**Evidence:** 17 tests pass; 146 pass across the memory + grain + signals + trading suites.

#### `#24` Live trades now have lineage — live_trades links rationale to outcome

*2026-08-29 · VERIFIED · validated* · `execution` `schema` `memory`

Closes the open CLAUDE.md TODO. Before this a live trade existed only in a chat transcript: paper_trades has no broker order id, no rationale, no live linkage, so nothing could be scored after the fact. live_trades records signal_id, broker_order_id, rationale, filters_passed and 'expected' - the prior, written before the outcome is known. A journal without a prior is history, not calibration.

**Evidence:** docs/memory/journal.py; live_trades table; REFI recorded as entry #1 (status exit_pending).

#### `#9` Offering participation and exercises-at-strike were read as open-market conviction

*2026-08-23 · VERIFIED · validated* · `data-integrity` `insiders` `fixed`

Form 4 code 'P' covers open-market buys, registered-offering participation and exercises at strike alike, and the collector flattened OpenInsider's qualified string ('P - Purchase+OE') to bare 'P' before storage. Intel's CEO bought 105,263 shares at exactly $95.00 INSIDE a $20B upsized offering (210.5M new shares) and the pipeline scored it as a $10M conviction buy. Fixed: preserve acquisition_code; derive acquisition_channel from a bar-range test — an open-market fill must print inside that session's low-high range. Below the low = off-market (offerings price at a discount); above the high = data anomaly, labelled separately.

**Evidence:** INTC $95.00 vs 95.35-98.35 session range. MSTR $99.62 vs 132.76-139.78. Zero false positives against KEEL/CC/OPEN open-market buys. After widening bar coverage to 396/405 form4 rows: 15.6% of all Form 4 'purchases' were not open-market priced.

#### `#8` Roll-up rows were counted alongside the Form 4 rows they summarise (47% of the table)

*2026-08-23 · VERIFIED · validated* · `data-integrity` `insiders` `fixed`

OpenInsider's cluster view returns aggregate rows summing several Form 4 filings; 352 of 753 rows are roll-ups. They sat in the same table as their own components and the trigger counted both. Fixed with src/analysis/insider_grain.py: explicit row_grain, totals drawn from exactly one grain (named in verdict.basis), cluster status established by EITHER >=2 distinct named Form 4 buyers OR the presence of a roll-up.

**Evidence:** KEEL 2026-08-20 roll-up of 116,129 sh = CEO 58,888 + COO 26,472 + COO 30,769, confirmed against SEC filings.

#### `#7` insiders table was 78% duplicate rows, inflating every cluster count

*2026-08-23 · VERIFIED · validated* · `data-integrity` `insiders` `fixed`

No UNIQUE constraint and a plain INSERT. OpenInsider's cluster / CEO-CFO / purchase views overlap, so each trade landed several times per run and again on every later run: 3,400 rows -> 753 distinct. Because the cluster trigger counts rows, one CEO purchase read as a seven-buyer cluster — Intel's '7 insiders bought $69,999,895' was a single $10.0M purchase counted seven times. Fixed with INSERT OR IGNORE plus a unique index on the Form 4 natural key.

**Evidence:** Verified live: a later collector run offered 204 rows and stored 4. Under the old code all 204 would have inserted.

#### `#6` Split contamination in outcomes.py fabricated forward returns up to +707%

*2026-08-23 · VERIFIED · validated* · `data-integrity` `outcomes` `fixed`

src/analysis/outcomes.py used price_at_signal (captured live, unadjusted) as the baseline against price_bars closes (retroactively split-adjusted). Mixing adjustment bases fabricates returns: SOXS 2026-05-22 recorded +706.78% at 5d, SPCX +593.24%. Those two rows alone lifted velocity_spike's 5-day mean from +5.33% to +34.76% while barely moving the median — the signature of outlier contamination. Fixed in v1.1.0: baseline is always the signal-day bar close, plus a _split_boundary() guard that leaves an outcome NULL rather than writing a number across a >2x or <0.5x single-session discontinuity.

**Evidence:** SOXS bars: $1,146.15 close on 05-22 -> $62.18 on 05-26, volume 1.88M -> 40.4M. price_at_signal was $7.67.

---

## Decisions

*Choices made, with the reasoning that would reverse them.*

#### `#42` User decided both open questions from #38/#41: leave paper admission trigger-blind, partially widen sentiment top_n 20->50

*2026-09-04 · VERIFIED · validated* · `decision` `paper-trading` `sentiment`

Presented as two explicit choices 2026-09-03. (1) Paper-book admission (#38): user chose 'leave trigger-blind' -- no code change to paper_trading.py/main.py admission logic. velocity_spike keeps consuming most of the 40 slots by volume; this is accepted as the cost of an honest, unbiased out-of-sample re-test per #29's design intent. (2) Sentiment scope (#41): user chose 'widen partially, top_n ~50' over leaving it at 20 or widening fully to the ~163-ticker universe. Implemented as #42.

**Evidence:** User response to AskUserQuestion, 2026-09-03

#### `#40` Rethought 2026-09-03: still no live trade. insider_cluster now 5/20 independent dates; nothing clears #19

*2026-09-03 · VERIFIED · validated* · `execution` `review` `decision`

User asked to rethink and recommend next action (second review same day). Re-verified account (651470783: 197.12 cash, no positions, no new orders -- unchanged) and re-ran the edge-by-type query fresh rather than trusting the prior turn's numbers: insider_cluster grew to n=10 / 5 independent dates (was 4 at the last check ~16h earlier), avg_fwd_10d +4.57%, hit_rate_10d 60%, still the only trigger anywhere near candidate status and still well short of #19's 20-independent-date bar. velocity_spike (n=42, 1 independent date, avg_fwd_10d -2.16%, hit 33.3%) and 'combined' (n=3, 2 dates, avg_fwd_10d -4.79%) both look actively bad; news_sentiment_bullish (n=9, 3 dates, avg +2.61%/77.8% hit) is promising on paper but dormant and too thin to weigh. guard.check('action:live_trade') still returns BLOCKED by #19. Decision unchanged: continue paper-only. The concrete next action taken this turn was not a trade but a process finding (#38) about paper-capacity allocation, plus an open question (#39) about the news_sentiment_bullish dry spell -- both non-live, both logged for the user's visibility and, for #38, explicit direction before any admission-logic code change is made.

**Evidence:** get_portfolio/get_equity_orders account 651470783, 2026-09-03T16:43Z; signals table edge-by-type + independent-date query, same timestamp

#### `#37` Reviewed 2026-09-03: paper-only (#19) reconfirmed, no real trade placed

*2026-09-03 · VERIFIED · validated* · `execution` `review` `decision`

User asked to review and make decisions. Reviewed: account flat at 197.12 cash, no new orders since the REFI close. First unsupervised production run of the #12/#21/ownership_change_pct fixes completed clean 2026-09-02 18:30-18:37 (pipeline_runs id=10, status=ok): 162 tickers analyzed technically (67 insider-only), 64/64 insider-only tickers got a bar-close price fallback, 28 signals from 163 tickers (96 velocity + 67 insider-only) -- fixes are working in production, not just in tests. insider_cluster edge update: n grew 6->10 measured outcomes, but still only 4 of the 20 independent dates decision #19 requires, and hit_rate_10d MOVED FROM 83.3%% TO 60%% as n grew -- exactly the kind of early-sample instability #19 exists to wait out, not evidence to override on. Decision: guard.check('action:live_trade') still returns BLOCKED by #19, and that block is left in place. No trigger has cleared the retest_when bar. 'Review and make decisions' is not read as authorization to place a live order without the specific-order-plus-explicit-confirmation step this project has used for every real trade to date -- that step still applies if the user wants to override #19.

**Evidence:** pipeline_runs id=10; logs/pipeline.log 2026-09-02 18:37:38-39; get_signal_edge_by_type() insider_cluster n=10, hit_rate_10d=60.0; get_portfolio account 651470783 = 197.12 cash

#### `#34` Paper book cap raised 10->40 (paper money, zero downside) -- #30's 'no rotation exists' claim was wrong, corrected here

*2026-09-02 · VERIFIED · validated* · `paper-trading` `correction` `capacity`

CORRECTION to #30: I claimed 'no time-based or conviction-based rotation appears to evict old paper positions.' That was wrong -- I had not read the code. src/trading/paper_trading.py:update_positions_from_bars() replays daily bars through walk_bars() and applies stop_loss_pct(-10%)/take_profit_pct(+20%)/hold_days(30) exits correctly, called every pipeline run BEFORE new signals are generated. The 8 positions open since 2026-08-19/20 simply had not reached 30 days yet (13-14 days old when #30 was written) -- the mechanism is working as configured, not broken. The REAL, correctly-identified problem in #30 stands: a 10-slot cap against 28 signals/day is a severe bottleneck that starves the experiment of the independent-date diversity #1's retest_when needs. Since paper trading risks no real capital, raised max_open_positions 10->40 in config/config.yaml (4x, absorbs a full high-signal day with buffer, still bounded rather than unlimited). Left hold_days/stop/target unchanged -- those are the parameters actually being measured, not the bottleneck.

**Evidence:** src/trading/paper_trading.py:update_positions_from_bars/_close_position, src/trading/engine.py:walk_bars; config/config.yaml max_open_positions

#### `#26` The ledger gate is installed at the trade chokepoint, not scattered across call sites

*2026-08-31 · VERIFIED · validated* · `memory` `execution` `architecture`

journal.open_trade() is the one function every live trade must pass through, so guard.check() lives there. A block is NOT absolute - you may override - but override_reason is REQUIRED and gets written into the row along with the blocking entry ids. 'We traded anyway because X' becomes part of the record rather than an undocumented exception. main.py also runs an advisory ledger pre-flight after signal generation: it reports which generated signals have a recorded failure against their trigger, but deliberately does not drop them. Reporting there, hard gate at the trade.

**Evidence:** docs/memory/journal.py open_trade(); main.py ledger pre-flight; tests/test_memory.py TestTradeLineage. Verified end-to-end: a live trade is currently blocked by #19.

#### `#23` Memory is enforced, not advisory — guard.py gates actions against the ledger

*2026-08-29 · VERIFIED · validated* · `memory` `architecture`

A read-me ledger fails exactly when it matters: mid-task, under momentum. guard.py turns entries with blocks=1 into a programmatic check. Call check('trigger:X','action:buy') before acting; it returns blocked plus the citing entry id. Matching is a CONJUNCTION - every target an entry names must be in the query - so an entry about 'velocity_spike + buy' does not fire on an unrelated buy. A clean verdict means 'nothing recorded forbids this', NOT 'this is a good idea'.

**Evidence:** docs/memory/guard.py; verified across 5 cases incl. the any-match bug that wrongly blocked insider_cluster.

#### `#22` paper_trades.pnl is a dead column — annotated, not migrated

*2026-08-29 · VERIFIED · validated* · `schema` `correction`

pnl is never written and never read; every code path and dashboard uses profit_loss, which is fully populated. An earlier session flagged the NULLs as a defect; that was a mis-read of the schema. Left in place per the historical-preservation rule rather than migrated, since removing it has blast radius and no benefit.

**Evidence:** grep for pnl/profit_loss across src/; 22/22 closed trades have profit_loss, 0 have pnl.

#### `#19` Closed the REFI position and reverted to paper-only until a real sample exists

*2026-08-29 · VERIFIED · validated* · `execution` `experiment` `risk`

Exited at roughly -$3 on $195.30. Reasoning: the pipeline half of the experiment succeeded and is proven, the signal half has no measured edge, and with zero edge the expected value of holding is approximately zero minus costs (simulated 60 trading days, zero drift: mean -$2.08, 39% chance of profit, 5th/95th percentile -$14.94/+$28.19). Keeping capital tied up to keep testing already-proven plumbing was not worth it. Reverse this decision when a trigger shows measured edge across independent observation dates.

**Evidence:** Exit order 6a936499-0d8d-4df3-9769-097f04e22576, limit $10.55.

***re-test when:** a trigger shows measured edge across >=20 independent observation dates*

**ENFORCED** — blocks: `action:live_trade`

#### `#15` Ran one live $200 execution test (REFI) to validate the order path end to end

*2026-08-25 · VERIFIED · validated* · `execution` `experiment`

Selected REFI as the only candidate clearing all four filters: two named open-market Form 4 buyers (both Co-CEOs), corroborated by a company press release (~54,000 sh / ~$673,000 by officers and directors), the lowest stop-out probability in the candidate set (14% vs 76-85% for the high-volatility names), and no earnings inside the window. Entry 18 sh @ $10.85 on 2026-08-25, $195.30. The purpose was to prove the execution path, not to express a view — there was no measured edge behind it and that was stated at the time.

**Evidence:** Order 6a8cd230-bf1c-498a-a40c-43c205b0f3e3, filled 09:30:00 ET, zero fees.

---

## Superseded

*Retained per the historical-preservation rule. Read the superseding entry instead.*

#### `#41` Root cause of the news_sentiment_bullish dry spell: sentiment collection is capped to the top 20 velocity-tracked tickers, never the insider-only universe  — **SUPERSEDED by #43**

*2026-09-03 · VERIFIED · superseded* · `sentiment` `data-quality` `root-cause` `api-cost`

Answers #39. main.py line 272: top_tickers = list(tracked_tickers)[:20], where tracked_tickers = db.get_tracked_tickers(days=7) -- a mention/velocity-derived set, config alphavantage.top_n=20. Both collect_alphavantage() and collect_vader() are called with this same 20-ticker list (main.py ~line 346/357). The Step 3 sentiment_data merge (main.py ~line 472) DOES loop over all_ticker_universe (the wide, post-#36 163-ticker set) but that only re-keys sentiment that was already collected -- it cannot manufacture sentiment for a ticker that was never in the 20-ticker collection call. Net effect: none of the 67 insider-only tickers has ever had sentiment collected, and even within the velocity-tracked universe, only the top 20 by 7-day mention activity get scanned per day. So news_sentiment_bullish's addressable universe was always much narrower than velocity_spike's or (post-#36) insider_cluster's, which explains both the low all-time volume (9 signals total) and this specific dry spell (whichever names cleared top-20 in the last 15 days apparently didn't also clear _check_positive_sentiment()'s bullish threshold). This is the same class of bug as #12/#31/#36 (narrow ticker universe hides a trigger) but NOT the same class of fix: technical_data's widening was free (src/metrics/technical.py is DB-only, zero API calls per its own docstring). Sentiment collection is not free -- Alpha Vantage is metered (articles_per_ticker=50, and Finnhub's sentiment endpoint is already disabled elsewhere in this same pipeline for requiring a paid plan) and VADER scrapes Yahoo Finance live per ticker, so widening from 20 to ~163 tickers is an ~8x increase in external call volume with real rate-limit/cost exposure, not a no-cost fix like #36 was. Left unimplemented pending explicit direction -- flagging the tradeoff rather than choosing it unilaterally, consistent with how #38's paper-admission question was also left for the user.

**Evidence:** main.py lines 271-272, 346, 357, 472-477; config/config.yaml collection.alphavantage.top_n=20

#### `#39` news_sentiment_bullish has not fired since 2026-08-19 despite steady daily sentiment collection  — **SUPERSEDED by #41**

*2026-09-03 · VERIFIED · superseded* · `sentiment` `data-quality` `open`

All 9 news_sentiment_bullish signals ever generated cluster on just 3 calendar dates (2026-04-02, 2026-05-17, 2026-08-19). Confirmed via logs/pipeline.log that sentiment collection itself is running every scheduled cycle and is not silently broken: VADER scraped ~10 tickers/day and Alpha Vantage collected sentiment for 20 tickers/day on both 2026-09-01 and 2026-09-02 (Finnhub sentiment endpoint is skipped -- known, requires paid plan, not new). Root cause of the 15-day dry spell not yet confirmed: candidates are (a) the sentiment collectors scan a small, possibly static ~20-30 ticker list that does not track the broader 163-ticker universe now evaluated post-#36 fix, analogous to the #12/#31/#36 narrow-universe bug already fixed for technical_data, or (b) _check_positive_sentiment()'s threshold is simply rarely cleared in the current headline mix. Not investigated further this turn -- the existing sample (n=9, 3 dates) is already too thin to matter for any near-term decision, so this is logged for a future session rather than chased now.

**Evidence:** logs/pipeline.log grep 'sentiment' 2026-09-01/09-02; signals table GROUP BY signal_type='news_sentiment_bullish'

#### `#31` Insider clusters can now signal without mention chatter -- generate_signals() iterates the union of tickers  — **SUPERSEDED by #36**

*2026-09-02 · VERIFIED · superseded* · `architecture` `insiders` `fix`

src/signals/generator.py: changed 'for ticker in velocity_data.keys()' to 'for ticker in (set(velocity_data.keys()) | set(insider_data.keys()))', with vel/price/tech/sentiment all defaulting via .get(ticker, {}) instead of direct indexing (the old code would KeyError on velocity_data[ticker] for an insider-only ticker). Necessary but NOT sufficient on its own: insider_cluster contributes a flat 25 conviction points against the production 40-point floor (config/config.yaml thresholds.minimum_conviction), so a companion fix was required in main.py -- technical_data and sentiment_data were ALSO scoped to velocity_data.keys() only, so a cluster-only ticker had no second trigger available to clear 40. Widened both to the same union (technical_data is DB-only / zero API cost per its own docstring; sentiment_data merge just re-keys already-fetched dicts, also free). Also added a price fallback (Database.get_latest_bar_closes(), free price_bars data) for tickers the Finnhub-backed  table doesn't cover, reused for paper-trade entry pricing too (was a second, separate Finnhub-only lookup that would have silently dropped every insider-only paper trade candidate even after signal generation fixed). Verified against the LIVE database, read-only, 2026-09-02: union was 160 tickers (100 velocity + 60 insider-only after dedup), PRTS fired (insider_cluster + technical_breakout, conviction 59) -- a signal that was structurally impossible before this fix. 15 new tests added across test_signals.py/test_database_models.py; full suite 327 passed / 1 pre-existing skip.

**Evidence:** src/signals/generator.py, main.py Step 2b/3, src/database/models.py:get_latest_bar_closes; live read-only run 2026-09-02 produced PRTS conv=59

#### `#30` Paper book has been at its 10-position cap since 2026-08-19/20 -- new signals cannot be tested  — **SUPERSEDED by #34**

*2026-09-02 · VERIFIED · superseded* · `paper-trading` `capacity` `operations`

2026-09-01 run generated 28 signals (top: GO conviction 77, insider_cluster + mentions velocity, $403,900 rollup buy; also USO 72, GPRO 69) and created ZERO new paper trades -- every candidate hit 'Max open positions (10) reached, skipping <ticker>' except RDDT which already had an open position. 8 of the 10 open slots have been unchanged since 2026-08-19/08-20 (12+ days); the other 2 (TSLA, AMZN) opened 2026-08-31. No time-based or conviction-based rotation appears to evict old paper positions to make room. Net effect: the experiment is not currently testing new signals, including the exact insider_cluster type that open question #12 flagged as under-tested, and today's top candidate (GO) got no paper-trade evaluation at all. Needs a decision: raise the cap, add position rotation/expiry, or manually close stale paper positions -- not implemented here, flagging for a decision.

**Evidence:** logs/pipeline.log 2026-09-01 18:37:32-18:37:33 (28 signals -> 0 new paper trades, 'Max open positions (10) reached' x14); paper_trades table, 10 rows status=open, entry_date min 2026-08-19T21:32:59

#### `#21` min_insiders=2 cannot distinguish a two-person cluster from a twenty-person one  — **SUPERSEDED by #32**

*2026-08-29 · DERIVED · superseded* · `insiders` `limitation`

With roll-ups acting as an alternate route to cluster status, a genuine broad cluster and a bare two-buyer cluster produce identical verdicts. Roll-up rows carry no buyer count (the scraper blanks insider_name/title for them), so the information needed to grade cluster breadth is not collected. Worth investigating whether OpenInsider's cluster view exposes a count column that could be captured.

**Evidence:** 401 of 753 rows carry a name; all 352 roll-ups do not.

#### `#12` Insider clusters cannot signal without Reddit chatter — 44 live clusters were invisible  — **SUPERSEDED by #31**

*2026-08-24 · VERIFIED · superseded* · `architecture` `insiders` `blocker`

generate_signals() iterates velocity_data.keys(), so a qualifying insider cluster on a ticker nobody posts about can never produce a signal. On 2026-08-24 there were 44 live qualifying clusters and almost none could signal; CC had a genuine cluster and produced nothing for exactly this reason. This structurally subordinates the only non-negative trigger to social mentions. Proposed fix: iterate the union of velocity tickers and tickers with live clusters.

**Evidence:** Observed during the 2026-08-24 signal generation run. 33 signals produced, 29 of them velocity_spike.
