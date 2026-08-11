# Contributing

Bug reports, corrections to the cricket domain logic, and answers to the open questions are
all welcome. Corrections to the cricket especially — the data cleaning encodes claims about
franchise history, and someone who follows the sport more closely than I do will spot an
error faster than a test will.

## Setup

```bash
git clone https://github.com/Surge77/scorebook.git
cd scorebook
python -m venv .venv
.venv/Scripts/activate          # Windows;  source .venv/bin/activate elsewhere
pip install -e ".[dev,notebook]"

pytest                          # offline, ~5 seconds
```

A fresh clone works with no network: `data/sample_deliveries.csv` is committed. You only
need `scorebook fetch` to work with all 19 seasons.

## Before you open a pull request

```bash
ruff check .
pyright
pytest --cov --cov-fail-under=90
```

All three must pass. CI runs them on Python 3.11 and 3.12, plus an integration job that
downloads the real archive and a smoke job that regenerates the sample.

## The rules of the codebase

**Unit tests never touch the network.** This is enforced by an autouse fixture in
`tests/conftest.py` that fails any unmarked test opening an HTTP connection. If your test
needs the real archive, mark it `@pytest.mark.integration`. If it needs to exercise the
download path, serve a fixture from `tmp_path` over `file://` — that still goes through the
real urllib code.

**Cleaning functions return new frames.** No step mutates its argument. This is what lets
notebook cells be re-run in any order without the data silently drifting.

**Analytical choices do not go in the package.** If a change requires picking a threshold,
defining a category boundary, or making a claim someone could reasonably dispute, it belongs
in a notebook where the choice is visible. See
[ADR 0006](docs/decisions/0006-analysis-in-notebooks.md). `over = floor(ball)` is
definitional and belongs in `clean.py`; `phase = "death" if over >= 15` is an argument and
does not.

**Assumptions about the upstream format go in `data/schemas.py`.** One place, so a Cricsheet
change fails once with a useful message.

**Every number in the docs was measured.** If you add a figure — a row count, a null
percentage, a memory footprint — run the code and paste the real output. Do not estimate.

**No new dependencies without a reason that survives scrutiny.** The download uses stdlib
`urllib` rather than `requests` because one HTTPS GET does not justify a dependency. The
package imports `numpy` nowhere, despite pandas depending on it, because importing a
transitive dependency is a break waiting to happen.

## Especially welcome

- **What `actual_delivery` actually means.** It is undocumented upstream and disagrees with
  `ball` on 35,647 rows. [ADR 0002](docs/decisions/0002-ball-not-actual-delivery.md) explains
  what was chosen and admits it is unverified. A definitive answer, ideally from Cricsheet,
  would close a real gap.
- **A reader for the `_info.csv` files.** 1,243 files in key-value long format, holding toss
  and match winner. Needed for question 4.
- **Corrections to `clean.TEAM_RENAMES`.** It claims Deccan Chargers and Sunrisers Hyderabad
  are separate franchises, and that Rising Pune Supergiant(s) is one. If either is wrong,
  say so — with a source.
- **Answers to the questions** in `docs/questions.md`, written up per the rules in
  `docs/results.md`: one number, one caveat, and how it could be wrong.

## Commits

Conventional commits:

```
feat(clean): read match winners from the _info files
fix(loaders): delete the .part file when a download is rejected
docs(adr): record why defunct franchises are not merged
test(clean): cover a season spanning two calendar years
```

One logical change per commit.

## Branches

Branch from `main` as `feature/<description>` or `fix/<description>`. Never commit to `main`
directly.

## Reporting a bug

Open an issue with the command you ran, the output you got, and the output you expected. If
it involves the data, include the row count `scorebook describe` reports — a mismatch
against 295,732 usually means the archive changed rather than the code broke.

## Questions

Open a [question issue](https://github.com/Surge77/scorebook/issues/new/choose). Ones about
the cricket are as welcome as ones about the code.
