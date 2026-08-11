# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.1] - 2026-08-11

A verification pass over 0.1.0. Everything below was found by running the code and
measuring, not by reading it.

### Fixed

- **The `category` dtype was inventing rows in a groupby.** Filtering to one season and
  grouping by team returned 15 rows for the 10 teams that played, with five defunct
  franchises credited with 0 runs — because a category column keeps its full value list and
  `groupby` defaults to `observed=False`. Self-inflicted by the memory optimisation, and
  exactly the silent-wrong-answer class this repo documents. Added
  `clean.drop_unused_categories`, documented it as README trap 4 and in the data dictionary,
  demonstrated it live in the notebook, and pinned both the broken and fixed behaviour in
  `tests/test_clean.py` so it cannot drift.
- **`start_date` loaded as text**, so `frame[frame.start_date > "2020-01-01"]` was a string
  comparison wearing a date comparison's clothes. It happens to work for ISO-8601 and would
  fail silently for anything else. Now parsed to `datetime64` in the loader, for both the
  archive and the sample path, with the format passed explicitly so an upstream change fails
  loudly. Side effect: the loaded frame dropped from 38 MiB to 21 MiB.
- **CI asserted exact row counts.** `grep -q "rows      295,732"` would have gone red the
  first time Cricsheet published the 2027 season — turning a routine upstream update into a
  broken build. Replaced with lower-bound checks; the sample job now asserts its two matches
  and two season formats rather than an exact row count.
- **Stale reference** to a `clean.season_to_year` that was deliberately never written.
- **`DEFUNCT_TEAMS` was dead code.** Now asserted disjoint from `TEAM_RENAMES`, so it
  documents a real invariant.

### Changed

- Every memory figure in the docs was re-measured and corrected. The earlier "~10 MiB" and
  "both levers are worth about the same" were both wrong. Measured: all 27 columns as
  `object` 227 MiB, 16 as `object` 159 MiB, all 27 as `category` 90 MiB, 16 as `category`
  21 MiB. `usecols` is worth 1.4×, the dtype 2.5× — the dtype is the bigger lever, which is
  the opposite of the usual advice.
- The notebook is now **executed** as part of verification, which it was not before release.

## [0.1.0] - 2026-08-11

First release. The plumbing, the documentation, and five questions written down before any
analysis. **No findings yet** — `docs/results.md` is deliberately a stub.

### Added

- **Loader** for Cricsheet's `ipl_csv2.zip`. Caches to `~/.cache/scorebook/`, downloads to
  a `.part` file so an interrupted transfer cannot masquerade as a valid archive, size- and
  zip-checks before caching, and streams one member with `ZipFile.open()` rather than
  extracting.
- **Column contract** in `data/schemas.py` — every assumption about the upstream format in
  one place. Validates the header alone before parsing 295,732 rows, tolerates new columns,
  refuses missing ones, and names the file to edit when it fails.
- **Cleaning** limited to transforms with one correct answer: `season_year` from
  `start_date`, `over` from `ball`, extras nulls to zero, structurally empty columns
  dropped, renamed franchises canonicalised. Every function returns a new frame.
- **`scorebook` CLI** — `fetch` and `describe`, the latter with `--sample` for offline use
  and `--clean` to report what cleaning changes. No `analyse` verb, on purpose.
- **Six ADRs**, each recording what the decision cost.
- **Stratified sample** (`data/sample_deliveries.csv`, 458 rows): the first IPL match and
  the most recent one, so both season formats and both generations of team names are
  present. A random sample would contain neither.
- **64 tests, 99% coverage**, gate at 90. Plus a conftest fixture that fails any unmarked
  test opening an HTTP connection — added after a CLI test quietly downloaded the real 6.8
  MB archive and passed.

### Documented, not solved

- **`actual_delivery` disagrees with `ball` on 12.05% of rows** and is undocumented
  upstream. This release uses `ball` and states the exposure in
  [ADR 0002](docs/decisions/0002-ball-not-actual-delivery.md) rather than claiming the
  choice is verified.
- **The 1,243 `_info.csv` files are unused.** They hold toss and match winner in key-value
  long format. Question 4 needs them, so question 4 may be deferred.

[0.1.1]: https://github.com/Surge77/scorebook/releases/tag/v0.1.1
[0.1.0]: https://github.com/Surge77/scorebook/releases/tag/v0.1.0
