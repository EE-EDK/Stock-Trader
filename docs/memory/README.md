# Project Memory

Persistent, append-only record of what has been tried in this project — what worked,
what did not, and what is still unresolved. Its purpose is to stop each fresh agent
session from re-deriving context that a previous session already paid for, and from
re-attempting approaches that were already proven not to work.

## Files

| File | Role |
|---|---|
| `ledger.jsonl` | **Source of truth.** One JSON object per line, append-only, never edited in place. |
| `LEDGER.md` | **Generated view.** Rewritten from the JSONL on every write. Never hand-edit — your changes will be overwritten. |
| `memory.py` | CLI: `add`, `list`, `supersede`, `render`, `seed`. Python stdlib only. |
| `seed.json` | Initial import (2026-08-23 → 2026-08-29 signal-validation work). Kept for provenance. |

## Reading it

`AGENTS.md` §Session Startup makes this step 2. At minimum, read the
**"Read this first"** block at the top of `LEDGER.md` — it lists the
do-not-repeat items and the open blockers in one screen.

```bash
python docs/memory/memory.py list --kind failure      # what does not work
python docs/memory/memory.py list --status open       # unresolved questions
python docs/memory/memory.py list --tag edge --full   # everything about signal edge
python docs/memory/memory.py list --id 7 --full       # one entry in detail
```

## Writing to it

Add an entry when you learn something a future session would otherwise have to
rediscover. The bar is *"would someone waste an hour without this?"* — not
*"is this interesting?"*

```bash
python docs/memory/memory.py add \
  --kind failure --status validated --confidence VERIFIED \
  --title "One-line claim, stated as a conclusion" \
  --detail "What was tried, what happened, and what to do instead." \
  --evidence "The query, file, order id, or measurement that proves it." \
  --tags edge,insiders
```

`LEDGER.md` regenerates automatically. Commit both files together.

### Fields

| Field | Values | Notes |
|---|---|---|
| `kind` | `finding` `failure` `decision` `fix` `question` | `failure` and `question` surface at the top of the ledger |
| `status` | `validated` `refuted` `open` `superseded` | |
| `confidence` | `VERIFIED` `DERIVED` `RECALLED` | Technical Editor Protocol v5.4 §III |
| `evidence` | free text | **Required in practice.** An entry without evidence is an opinion. |
| `tags` | comma-separated | Use existing tags before inventing new ones — check `list` output |

`VERIFIED` means confirmed against a primary source: a query result, a file, an
order id, a filing. `DERIVED` means computed from verified data. `RECALLED` means
it came from conversation or memory and has **not** been re-checked — treat those
as leads, not facts.

## Correcting an entry

**Never edit or delete.** That is the project's historical-preservation red line
(`AGENTS.md` §Red Lines). Supersede instead:

```bash
python docs/memory/memory.py add --kind finding --status validated \
  --confidence VERIFIED --title "The corrected claim" \
  --detail "..." --evidence "..." --supersedes 7
```

Entry #7 is retained, marked `SUPERSEDED by #N`, and moved to the bottom of
`LEDGER.md`. Being able to see what was previously believed — and why it changed —
is usually as valuable as the correction.

## What belongs here vs. elsewhere

| Goes here | Goes elsewhere |
|---|---|
| "velocity_spike has −7.73pp of 30d alpha, don't trade it long" | Build commands → `CLAUDE.md` |
| "Reconciling roll-ups against components fails, 4/352" | Architecture rules → `GEMINI.md` |
| "SQLite writes fail over the device mount" | A full write-up → `docs/` (link it from the entry's evidence) |
| "The channel test only reaches rows that have a bar" | Code comments → the code |

Rule of thumb: this ledger holds **durable conclusions and their evidence**.
Long-form analysis goes in `docs/` and gets referenced from an entry rather than
pasted into it. See `docs/2026-08-29_signal_validation_learnings.md` for the
worked example the initial seed was drawn from.

## Maintenance

There is no automatic expiry. Entries stay until superseded. If a `question`
entry gets answered, add a `finding` that supersedes it — that way the ledger's
"Unresolved" block stays honest, which is the property that makes it worth
reading at the top of every session.

---

## Enforcement — `guard.py`

A ledger only helps if someone reads it, and that assumption fails exactly when it
matters: mid-task, under momentum, when the instruction is "just run it". Entries
marked `--blocks` with an `applies_to` list become a **programmatic gate**:

```python
from docs.memory.guard import check, require

v = check('trigger:velocity_spike', 'action:buy')
if v.blocked:
    raise RuntimeError(v.explain())

require('action:live_trade')      # raises if anything recorded forbids it
```

```bash
python docs/memory/guard.py trigger:velocity_spike action:buy   # exit 1 if blocked
```

**Matching is a conjunction.** Every target an entry names must appear in the query.
An entry about `trigger:velocity_spike + action:buy` does not fire on an unrelated
buy. Targets are namespaced free text — `trigger:`, `action:`, `env:`, `tool:`,
`config:`, `approach:`.

Currently enforced: `trigger:velocity_spike + action:buy`, `action:live_trade`,
`config:bracket_20_10`, `approach:rollup_reconciliation`,
`env:container + tool:yfinance`, `env:device_mount + tool:sqlite_write`.

> A clean verdict means *nothing recorded forbids this* — **not** *this is a good
> idea*. The ledger only knows what has already been measured.

To lift a block, supersede the entry. Do not delete it.

## Falsifiability — `sample_n` and `retest_when`

Every enforced entry states the sample it rests on and the condition that should
overturn it, so blocks get re-tested rather than calcifying:

```bash
python docs/memory/memory.py annotate 1 --sample-n 43 \
  --retest-when "n>=100 velocity_spike outcomes across >=20 independent dates"
```

Annotations are appended, never edited in place — the same pattern as corrections.

## Trade lineage — `journal.py`

Links a decision and its rationale to what actually happened. Lives in SQLite
(`live_trades` in `sentiment.db`), joinable to `signals` via `signal_id`, keyed on
`broker_order_id`.

```bash
python docs/memory/journal.py open --ticker X --side buy --qty N --order-id ... \
    --rationale "why this one" --expected '{"p_stop_30d":0.14,"stated_edge":null}'
python docs/memory/journal.py close --order-id ... --exit-price N --exit-reason stop
python docs/memory/journal.py report        # ledger + expectation vs outcome
```

Record `expected` **before** the outcome is known. That prior is what makes this a
calibration loop rather than a logbook — it lets you ask later whether your stated
reasoning was any good, not just whether the trade made money.
