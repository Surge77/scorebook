# Architecture

## The shape

```
cricsheet.org ──► loaders.download_archive() ──► ~/.cache/scorebook/ipl_csv2.zip
                                                          │
                              loaders.load_deliveries() ◄──┘
                                        │  usecols + category dtypes
                                        │  schemas.validate_columns()
                                        ▼
                                  raw DataFrame  (295,732 × 16)
                                        │
                              clean.prepare()
                                        │  drop_always_empty
                                        │  canonical_teams
                                        │  canonical_venues
                                        │  add_season_year
                                        │  add_over
                                        │  fill_extras
                                        ▼
                            analysis-ready DataFrame
                                        │
                    ┌───────────────────┴──────────────────┐
                    ▼                                      ▼
        describe.summarise()                    notebooks/01_explore.ipynb
        (counts, null profile)                  (the analysis — not in the package)
```

The same archive holds a second frame at a different grain, read separately:

```
        ipl_csv2.zip
              │  1,243 × <match_id>_info.csv   (key-value long format)
              ▼
        loaders.load_match_info()
              │  pivot to one row per match
              ▼
        match info DataFrame  (1,243 × 16)
              │  join on match_id
              ▼
        who won, where, and who won the toss
```

It is a separate call rather than part of `load_deliveries` because it opens 1,243 zip
members and four of the five questions never need it
([ADR 0007](decisions/0007-reading-the-info-files.md)).

## Why the package stops where it does

The hard line: **the package does things with one correct answer; the notebook does things
that need an argument.**

`over = floor(ball)` is definitional — Cricsheet documents `ball` as over-plus-delivery, so
there is no judgement in extracting the integer part. It belongs in `clean.py`.

`phase = "death" if over >= 15 else ...` is not definitional. Where the death overs start
is contested, the threshold changes the answer to Q1, and a reader is entitled to see the
choice being made. So it lives in the notebook, where it is visible and arguable, and
[ADR 0006](decisions/0006-analysis-in-notebooks.md) records why.

The same test applies everywhere. Collapsing `Kings XI Punjab` into `Punjab Kings` is
factual — one franchise, renamed. Collapsing `Deccan Chargers` into `Sunrisers Hyderabad`
is a claim about franchise continuity that happens to be false, so the code does not make
it ([ADR 0005](decisions/0005-team-names.md)).

## Module responsibilities

| Module | Owns | Deliberately does not |
|---|---|---|
| `data/schemas.py` | Every assumption about the file's shape: column names, dtypes, which nulls mean what | Touch a DataFrame |
| `data/loaders.py` | Network, cache, zip reading, column validation | Clean anything |
| `clean.py` | Definitional transforms, all returning new frames | Aggregate, or make analytical choices |
| `describe.py` | Counts and null profile — the "did this load right" surface | Interpret |
| `plots.py` | Figure styling and saving | Build charts or aggregate |
| `cli.py` | Two verbs: `fetch`, `describe` | Offer an `analyse` verb |

## Decisions worth knowing

**`schemas.py` is the single source of truth.** Every fact about the upstream format is
one import away, so a Cricsheet change fails in one place with a message naming the file to
edit — not as a `KeyError` from inside a groupby.

**Validation reads the header alone first.** `load_deliveries` parses zero rows to check
columns before parsing 295,732. A format change is reported by name in milliseconds rather
than after a full parse.

**Extra columns are allowed, missing ones are not.** Cricsheet added `actual_delivery`
without notice. A validator that rejected unknown columns would have broken on an upstream
addition that harmed nothing.

**The zip is never extracted.** `ZipFile.open()` streams one named member. Nothing is
written to disk, so a crafted archive has no path to traverse — see
[SECURITY.md](../SECURITY.md).

**Downloads land on a `.part` file first.** An interrupted download cannot leave a
truncated archive that later looks cached and valid.

**Every `clean` function returns a new frame.** No step mutates its argument, so the
notebook can re-run any cell in any order without the frame silently drifting — the single
most common source of irreproducible notebook results.

**Unit tests cannot reach the network, structurally.** A conftest fixture fails any
unmarked test that opens HTTP. It was added because a test quietly downloaded the real
archive and passed; `file://` stays allowed so the download path is still tested for real.

## Adding a model later

Nothing here would need restructuring. A `model.py` and `evaluate.py` would sit beside
`clean.py`, consume the prepared frame, and the CLI would gain a third verb. `plots.py`
already saves figures. That is why v1 is EDA-only rather than half a model.
