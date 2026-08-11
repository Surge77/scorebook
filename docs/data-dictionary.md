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

| Load strategy | Memory | Saving |
|---|---:|---|
| All 27 columns, default dtypes | 244 MiB | — |
| All 27, category dtypes on text | 107 MiB | 2.3× |
| The 16 in `USED_COLUMNS`, category dtypes | **38 MiB** | 2.8× more, 6.4× total |

19 teams, 60 venues, 10 dismissal types across 295,732 rows — which is why the text columns
load as `category`. The two levers turn out to be worth about the same, which is the useful
part: dtype tuning gets the attention, but simply not reading 11 unused columns is just as
effective.

One trap: reading all 27 columns in chunks makes pandas infer dtypes per chunk, and the
all-null columns (`non_boundary`, `fielder_3`) come out as mixed types with a
`DtypeWarning`. Under this project's `filterwarnings = ["error"]` that is a test failure, so
the loader passes `low_memory=False` to parse in a single pass.

## Grain

One row per **delivery**, per innings, per match. Not per over and not per ball-faced: a
wide is a row but not a legal delivery, so counting rows in an over overcounts unless you
exclude them.
