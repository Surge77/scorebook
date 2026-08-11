# 0004 — The season year comes from `start_date`, never from the season label

**Status:** accepted

## Context

`season` is a string, and three of the 19 values carry a slash:

| Label | Played |
|---|---|
| `2007/08` | 18 Apr – 1 Jun **2008** |
| `2009` | 18 Apr – 24 May 2009 |
| `2009/10` | 12 Mar – 25 Apr **2010** |
| `2020/21` | 19 Sep – 10 Nov **2020** |
| `2021` … `2026` | plain years |

Q2 — has scoring inflated across 19 seasons? — needs a sortable numeric year. The obvious
move is a string rule over the label.

## Decision

Derive `season_year` from `start_date.dt.year`. Provide no string-parsing helper at all.
Raise `CleaningError` if any season ever spans two calendar years.

## Why

**No string rule is correct.** Both candidates fail, and they fail differently:

*Take the second part:* `2007/08` → 2008 ✅, `2009/10` → 2010 ✅, `2020/21` → **2021** ❌.
IPL 2020 was played entirely in 2020, moved to the UAE and shifted to September by the
pandemic. Cricsheet still labels it `2020/21`. This rule invents a 2021 season that already
exists separately, and merges two real seasons.

*Take the first part:* `2020/21` → 2020 ✅, but `2009/10` → **2009** ❌ — which collides with
the genuine, separate `2009` season played in South Africa. Two distinct seasons a year
apart collapse into one.

Both failures are **silent**. No exception, no warning: just a season-trend chart with one
fewer point than it should have and two seasons averaged together. On Q2, the question this
column exists for, that is the difference between a finding and an artefact.

**`start_date` has no such ambiguity.** Every IPL season to date was played inside a single
calendar year, so the date answers the question the label only gestures at.

**Raising beats guessing.** If the IPL ever runs across New Year, `add_season_year` fails
loudly and names this file. The alternative — silently picking the earlier or later year —
would reintroduce exactly the class of bug this decision exists to prevent.

## Cost

`add_season_year` needs a DataFrame with two columns, so it cannot be a pure
`str -> int` function. That makes it slightly awkward to unit test and impossible to reuse
on a bare season label — which is deliberate: a reusable string helper is the bug.

The one-year-per-season check runs a `groupby().nunique()` over 295k rows on every call.
Measured at well under a second, and it runs once per session, so it is not worth caching.

It also means this repo cannot process a competition whose seasons *do* straddle years —
England's county season, say — without a decision being made first. Correct behaviour: that
decision should be explicit, not inherited from IPL-shaped code.
