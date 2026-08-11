# 0003 — Three kinds of null, three treatments

**Status:** accepted

## Context

Most columns in this dataset are mostly empty:

| Column | Null % |
|---|---:|
| `other_wicket_type`, `other_player_dismissed`, `penalty`, `non_boundary`, `fielder_3` | 100.0 |
| `noballs` | 99.6 |
| `byes` | 99.7 |
| `legbyes` | 98.5 |
| `wides` | 96.7 |
| `wicket_type`, `player_dismissed` | 95.0 |

The reflex on seeing a 95%-null column is to drop it, and `dropna()` on this frame would
delete almost everything. Both reflexes are wrong, and for different reasons per column.

## Decision

Three groups, declared in `schemas.py` and applied in `clean.py`:

| Group | Columns | Treatment |
|---|---|---|
| `ALWAYS_EMPTY` | the five 100%-null columns | **drop** |
| `EXTRAS_COLUMNS` | `wides`, `noballs`, `byes`, `legbyes` | **fill with 0** |
| the rest of `INFORMATIVE_NULLS` | `wicket_type`, `player_dismissed` | **leave null** |

## Why

**The 100%-null columns are structurally empty, not missing.** Cricsheet's format is shared
across formats and competitions. `penalty` runs and second-dismissals-on-one-delivery are
real cricket events that have never occurred in an IPL match. The column carries no
information about IPL, so dropping it loses nothing.

**A null in `wides` is the number zero.** No wide was bowled. Leaving it null means the row
silently drops out of `sum()`, and worse, out of the *denominator* of any rate — which is
exactly what Q5 computes. Filling with 0 makes the value true rather than absent.

**A null in `wicket_type` is not a value at all.** No wicket fell. There is no dismissal
type to record. Filling it with `"none"` would create a category holding 95% of rows that
appears at the top of every `value_counts` and has to be manually excluded from every
groupby forever. Leaving it null means `dropna()`, `notna()`, and `groupby` (which skips
nulls by default) all do the right thing without being told.

The distinction is not pedantry: it decides whether `wicket_type.value_counts()` is
immediately useful or immediately misleading.

## Cost

Three rules instead of one is more to hold in your head, and the grouping lives in
`schemas.py` while the application lives in `clean.py` — two files to check rather than one.

`ALWAYS_EMPTY` is also an empirical claim about *this* archive, not a guarantee. If a future
IPL match ever awards penalty runs, that column stops being empty and this code will drop
real data. `tests/test_schemas.py` asserts the groups stay disjoint and reference real
columns, but nothing detects a column that *stops* being empty.

Accepted because the failure is small and visible: penalty runs are rare enough that their
absence would be noticed in a total, and the fix is to remove one entry from a frozenset.
