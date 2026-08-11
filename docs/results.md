# Results

> **Status: nothing answered yet.** This file is a stub. The five questions in
> [questions.md](questions.md) were committed before any analysis; the answers go here as
> they are found. See [ADR 0006](decisions/0006-analysis-in-notebooks.md) for why the
> analysis is not pre-built.

## How to fill this in

One section per question. Each needs, at minimum:

- **The number.** A single figure, with its units and its denominator.
- **The caveat.** What population the number is actually over, and what it does not cover.
- **The chart**, saved to `reports/` via `plots.save_fig` and referenced by filename.
- **How it could be wrong.** The aggregation you rejected, or the confound you could not
  control for.

A finding without a caveat is not finished. "Death overs average 9.8 runs per over against
7.1 in the middle overs" is half an answer; the other half is "this pools both innings, and
a second-innings chase behaves differently once the target is close".

---

## Q1 — Do runs per over spike in the death overs?

_Not yet answered._

## Q2 — Has scoring inflated across 19 seasons?

_Not yet answered._

## Q3 — Does a first-over wicket reduce the innings total?

_Not yet answered._

## Q4 — Which venue shows the largest home advantage?

_Not yet answered._ Blocked on the `_info.csv` files, which hold match winners in key-value
long format — see README "Known limits". Reporting this as deferred is a legitimate outcome.

## Q5 — Are wides and no-balls getting rarer?

_Not yet answered._

---

## What didn't work

_To be written._ At least one entry is expected here, and an empty section by the end
should be treated as a sign the questions were too safe rather than as a clean sweep.

Candidates already visible before starting:

- `actual_delivery` is unresolved, not understood — [ADR 0002](decisions/0002-ball-not-actual-delivery.md)
  documents the exposure honestly rather than claiming the choice is proven correct.
- Q4 may not be answerable with the data currently loaded.
