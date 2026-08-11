# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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

[0.1.0]: https://github.com/Surge77/scorebook/releases/tag/v0.1.0
