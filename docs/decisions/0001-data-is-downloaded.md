# 0001 — The archive is downloaded, not committed

**Status:** accepted

## Context

The project depends on one public archive: Cricsheet's `ipl_csv2.zip`, 6.8 MB, holding
295,732 ball-by-ball rows. Committing it would make the repository self-contained and
remove a network dependency from CI.

## Decision

Download on demand into `~/.cache/scorebook/`, outside the project. Commit only a small
locally generated sample, `data/sample_deliveries.csv` (458 rows, 63 KB).

## Why

**Licence.** Cricsheet publishes under its own terms. Redistributing someone else's data
inside an MIT-licensed repository muddies what the MIT licence actually covers — a reader
would reasonably assume MIT applies to everything in the tree, and for the data it does not.

**Size and permanence.** 6.8 MB in git history is there forever, for everyone who ever
clones. It also grows: a season is added every year, so the committed copy would go stale
and the repo would carry both the stale copy and its replacement.

**Attribution.** Downloading from source means users hit Cricsheet directly, see the terms,
and get the current data. Vendoring it silently makes this repo the apparent source.

**A stale copy is worse than no copy.** The archive gained the 2026 season in May. A
committed 2025 snapshot would quietly answer Q2 — the season-trend question — with a
missing year.

## Cost

`pytest -m integration` needs a network connection, and CI has a job that can fail for
reasons unrelated to the code.

Mitigated by making the default `pytest` run entirely offline. The committed sample is
generated locally, so a fresh clone works with no network at all — and the sample is
stratified rather than random (the first IPL match and the most recent one) precisely so it
still exercises both season formats and both generations of team names.

The remaining gap: the offline path never proves the real 27-column file parses. That is
what the integration job is for, and why it asserts measured row counts rather than merely
"it loaded".
