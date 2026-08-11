# Data dictionary

Source: `all_matches.csv` inside
[`ipl_csv2.zip`](https://cricsheet.org/downloads/ipl_csv2.zip).

Everything below was **measured** from the archive on 2026-08-11, not copied from
documentation: 295,732 rows, 27 columns, 1,243 matches, 19 seasons, 2008-04-18 to
2026-05-31.

## A warning about the upstream README

Cricsheet's bundled `README.txt` documents **22** columns. The file ships **27**. The five
undocumented ones are marked ⚠ below. One of them, `actual_delivery`, disagrees with the
documented `ball` column on 12.05% of rows — see
[ADR 0002](decisions/0002-ball-not-actual-delivery.md).

Treat undocumented columns as unverified. Extra columns appearing without notice is
exactly why `schemas.validate_columns` tolerates additions but not removals.

## Columns

Null percentages are of all 295,732 rows. **Loaded** marks the 16 columns in
`schemas.USED_COLUMNS`.

| Column | Type | Null % | Loaded | Notes |
|---|---|---:|:---:|---|
| `match_id` | int | 0.0 | ✅ | Cricsheet's own match id; joins to `<id>_info.csv` |
| `season` | **string** | 0.0 | ✅ | `2009` or `2007/08`. Never parse the year from this — [ADR 0004](decisions/0004-season-year.md) |
| `start_date` | date | 0.0 | ✅ | The authoritative source of the season year |
| `venue` | string | 0.0 | ✅ | 60 distinct; names are not normalised upstream |
| `innings` | int | 0.0 | ✅ | 1 or 2; **above 2 means a super over** |
| `ball` | float | 0.0 | ✅ | over.delivery — `0.3` is the 3rd ball of the 1st over |
| `actual_delivery` | float | 0.0 | ❌ | ⚠ undocumented; differs from `ball` on 35,647 rows |
| `batting_team` | string | 0.0 | ✅ | 19 names, ~14 franchises — [ADR 0005](decisions/0005-team-names.md) |
| `bowling_team` | string | 0.0 | ✅ | same normalisation applies |
| `striker` | string | 0.0 | ✅ | batter facing the delivery |
| `non_striker` | string | 0.0 | ❌ | available if you need partnerships |
| `bowler` | string | 0.0 | ✅ | |
| `runs_off_bat` | int | 0.0 | ✅ | excludes extras — add `extras` for the delivery total |
| `extras` | int | 0.0 | ✅ | total of the five extras columns below |
| `wides` | float | 96.7 | ✅ | null = 0 |
| `noballs` | float | 99.6 | ✅ | null = 0 |
| `byes` | float | 99.7 | ❌ | null = 0 |
| `legbyes` | float | 98.5 | ❌ | null = 0 |
| `penalty` | float | **100.0** | ❌ | empty in every IPL row |
| `non_boundary` | float | **100.0** | ❌ | ⚠ undocumented, and empty |
| `wicket_type` | string | 95.0 | ✅ | 10 values; **null means no wicket, kept null** |
| `player_dismissed` | string | 95.0 | ✅ | null when no wicket fell |
| `other_wicket_type` | string | **100.0** | ❌ | second dismissal on one delivery; never happens here |
| `other_player_dismissed` | string | **100.0** | ❌ | as above |
| `fielder_1` | string | 96.4 | ❌ | ⚠ undocumented; present only on dismissals |
| `fielder_2` | string | 99.8 | ❌ | ⚠ undocumented |
| `fielder_3` | string | **100.0** | ❌ | ⚠ undocumented, and empty |

## Three kinds of null, three treatments

Applying one rule to all of these loses information. See
[ADR 0003](decisions/0003-informative-nulls.md).

| Kind | Columns | Treatment |
|---|---|---|
| Structurally empty | `penalty`, `non_boundary`, `other_wicket_type`, `other_player_dismissed`, `fielder_3` | **dropped** — no information |
| Null means zero | `wides`, `noballs`, `byes`, `legbyes` | **filled with 0** — a null would drop the row from sums |
| Null means "did not happen" | `wicket_type`, `player_dismissed` | **left null** — a `"none"` category would dominate every `value_counts` |

## `wicket_type` values

`caught`, `bowled`, `run out`, `lbw`, `caught and bowled`, `stumped`, `retired hurt`,
`hit wicket`, `obstructing the field`, `retired out`.

Note `retired hurt` and `retired out` are not bowler dismissals. Counting "wickets per
bowler" without excluding them, plus `run out`, overstates bowling figures.

## Columns this package derives

| Column | From | Definition |
|---|---|---|
| `season_year` | `start_date` | Calendar year the season was played. Raises if a season ever spans two years rather than guessing. |
| `over` | `ball` | `floor(ball)`, zero-indexed. An over can hold more than 6 rows — wides and no-balls are re-bowled. |

**Not derived:** a `phase` column (powerplay / middle / death). Where the death overs begin
is an analytical choice to argue for, not a fact to hard-code —
[ADR 0006](decisions/0006-analysis-in-notebooks.md).

## Cardinality and memory

Two independent levers, measured across all four combinations:

| Columns | Text dtype | Memory |
|---|---|---:|
| all 27 | default (`object`) | 227 MiB |
| 16 (`USED_COLUMNS`) | default (`object`) | 159 MiB |
| all 27 | `category` | 90 MiB |
| 16 (`USED_COLUMNS`) | `category` | **21 MiB** |

So `usecols` alone is worth 1.4×, `category` alone 2.5×, and both together 10.6×. **The
dtype is the bigger lever**, by a clear margin — and on the 16 columns actually loaded it is
worth 7.4× on its own (159 → 21 MiB). `clean.prepare()` brings the frame to 19 MiB, because
filling the extras columns replaces float64 nulls with int16.

`start_date` is parsed to `datetime64` by the loader, which is itself worth ~17 MiB: 295,732
date strings become 295,732 int64s. It is done for correctness rather than memory — see
below — but the saving is real.

Where the saving comes from, per column:

| Column | Cardinality | `category` | `object` |
|---|---:|---:|---:|
| `venue` | 60 | 0.29 MiB | 24.3 MiB |
| `bowling_team` | 19 | 0.28 MiB | 21.1 MiB |
| `batting_team` | 19 | 0.28 MiB | 21.1 MiB |
| `bowler` | 578 | 0.62 MiB | 18.9 MiB |
| `striker` | 739 | 0.63 MiB | 18.8 MiB |
| `season` | 19 | 0.28 MiB | 17.3 MiB |

Note that cardinality barely matters at this row count — 739 distinct bowlers compress about
as well as 19 venues, because the win comes from storing 295,732 integer codes instead of
295,732 separate Python strings.

**The category dtype has a cost, and it is not memory.** See the groupby trap below.

One parsing trap: reading all 27 columns in chunks makes pandas infer dtypes per chunk, and
the all-null columns (`non_boundary`, `fielder_3`) come out as mixed types with a
`DtypeWarning`. Under this project's `filterwarnings = ["error"]` that is a test failure, so
the loader passes `low_memory=False` to parse in a single pass.

## The groupby trap that `category` buys you

A category column carries its full value list independently of the rows present, and
`DataFrame.groupby` on a categorical defaults to `observed=False` — one output row per
*category*, not per value actually present.

Measured on the real data:

```python
recent = deliveries[deliveries.season_year == 2026]
recent["batting_team"].nunique()                                  # 10 teams played
len(recent.groupby("batting_team", observed=False).size())         # 15 rows
```

The five extra rows are Deccan Chargers, Gujarat Lions, Kochi Tuskers Kerala, Pune Warriors,
and Rising Pune Supergiant — franchises that did not exist in 2026, each reported with **0
runs**. No error. pandas 2.2 emits a `FutureWarning` about the default, but nothing warns
that the answer gained five wrong rows.

Two fixes, both worth the habit:

```python
recent.groupby("batting_team", observed=True)      # the direct fix
clean.drop_unused_categories(recent)               # for frames handed to other code
```

pandas 3.0 makes `observed=True` the default and this disappears. Until then it is the price
of a 7.4× memory saving, and `tests/test_clean.py` pins the behaviour so it cannot change
unnoticed.

Note `filterwarnings = ["error"]` means a **test** that groups a categorical without
`observed=` fails outright on the `FutureWarning`. That is deliberate: better a red test than
a silently wrong table.

## Grain

One row per **delivery**, per innings, per match. Not per over and not per ball-faced: a
wide is a row but not a legal delivery, so counting rows in an over overcounts unless you
exclude them.
