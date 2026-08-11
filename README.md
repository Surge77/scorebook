# scorebook

Every ball of the IPL, 2008 to 2026 — 295,732 deliveries across 1,243 matches — loaded,
cleaned, and interrogated with five questions written down **before** the first chart.

A scorebook is the physical book cricket scorers have written matches into for 150 years.
The data here comes from [Cricsheet](https://cricsheet.org), which digitises it.

```bash
pip install -e .
scorebook fetch          # 6.8 MB, once per machine
scorebook describe       # what you actually got
```

## Why this project exists

Most beginner analysis projects use a dataset whose answer is already public. Titanic is
the canonical example: everyone knows women in first class survived, so the "finding" was
never in doubt and the project proves nothing.

This dataset keeps the one genuinely useful property of a known dataset — **you can check
your own arithmetic**, because match results are public — while the granular answers are
unknown. Nobody has published whether a wicket in the first over actually costs runs.

The five questions live in [docs/questions.md](docs/questions.md), committed before any
analysis, so the findings cannot be retrofitted to whatever the charts happened to show.

## What's in here, and what isn't

**In:** acquisition, validation, cleaning, a dataset summary, chart styling, tests, docs.
Everything that has one correct answer.

**Not in:** the analysis. `docs/results.md` is a stub, and the notebook's question
sections are empty. That is the point of the project, and
[ADR 0006](docs/decisions/0006-analysis-in-notebooks.md) explains the split.

## The four traps this data sets

Real datasets are not messy in the abstract. They are messy in specific ways, and each of
these produces a wrong number rather than an error. Three come from the data. The fourth
comes from the fix for the third — which is the more useful lesson.

### 1. `season` cannot be parsed from the season label

Cricsheet labels three seasons with a slash. There is no string rule that works:

| Label | Actually played | Second part | First part |
|---|---|---|---|
| `2007/08` | 2008 | ✅ 2008 | ❌ 2007 |
| `2009/10` | 2010 | ✅ 2010 | ❌ 2009 — collides with the real `2009` season |
| `2020/21` | **2020** | ❌ 2021 | ✅ 2020 |

Taking the second part is wrong for 2020/21. Taking the first part merges `2009/10` into
the separate, genuine `2009` season — two seasons become one and no error is raised.
`clean.add_season_year` derives the year from `start_date` instead, and refuses rather
than guesses if a season ever spans two calendar years.
([ADR 0004](docs/decisions/0004-season-year.md))

### 2. `ball` and `actual_delivery` disagree on 12% of rows

The archive ships 27 columns. Cricsheet's own README documents **22** — `actual_delivery`,
`non_boundary`, and `fielder_1/2/3` are undocumented. `ball` and `actual_delivery` differ
on 35,647 of 295,732 rows, so choosing the wrong one corrupts every per-over aggregate.

This package uses `ball`, because it is the one upstream actually specifies: *"a
combination of the over and delivery. For example, 0.3 represents the 3rd ball of the 1st
over."* ([ADR 0002](docs/decisions/0002-ball-not-actual-delivery.md))

### 3. Most nulls are not missing data

| Column | Null % | What the null means |
|---|---|---|
| `wicket_type` | 95.0 | no wicket fell on that delivery |
| `noballs` | 99.6 | no no-ball was bowled — the value is 0 |
| `penalty`, `non_boundary`, `fielder_3`, `other_*` | 100.0 | structurally empty in IPL |

Three different treatments, and using one rule for all of them loses information. The
100%-empty columns are dropped. The extras are filled with `0`, because that is the true
value and a null would drop the row out of any sum. `wicket_type` is **left null**, since
"no wicket" is not a dismissal type and a `"none"` category would dominate every
`value_counts`. ([ADR 0003](docs/decisions/0003-informative-nulls.md))

### 4. The `category` dtype invents rows in a groupby

This one is self-inflicted, which is why it is worth reading. Loading the text columns as
`category` cuts memory 7.4× — and a category column keeps its full value list regardless of
which rows are present, while `groupby` defaults to `observed=False`:

```python
recent = deliveries[deliveries.season_year == 2026]
recent["batting_team"].nunique()                             # 10 teams played
len(recent.groupby("batting_team", observed=False).size())    # 15 rows
```

Five phantom rows: Deccan Chargers, Gujarat Lions, Kochi Tuskers Kerala, Pune Warriors and
Rising Pune Supergiant, each credited with **0 runs** in a season none of them existed in.
pandas warns about the changing default; nothing warns that the answer grew five wrong rows.

Fix with `observed=True`, or `clean.drop_unused_categories(frame)` after filtering. pandas
3.0 makes it the default. `tests/test_clean.py` pins the behaviour both ways so it cannot
drift.

**The general lesson:** an optimisation changed an answer. Worth remembering the next time a
dtype choice looks purely mechanical.

Bonus, not a trap so much as a judgement call: 19 team names cover about 14 franchises.
`Rising Pune Supergiants` (2016) and `Rising Pune Supergiant` (2017) differ by one letter and
are the same team. Meanwhile Deccan Chargers and Sunrisers Hyderabad look like a rebrand and
are **not** one. ([ADR 0005](docs/decisions/0005-team-names.md))

## Quickstart

```bash
python -m venv .venv && .venv/Scripts/activate     # Windows
pip install -e ".[dev,notebook]"

scorebook fetch                                     # cache the archive
scorebook describe --clean                          # summary + what cleaning changes
jupyter lab notebooks/01_explore.ipynb              # answer the five questions
```

No account, no API key, no credentials — Cricsheet is a public download.

In Python:

```python
from scorebook import clean
from scorebook.data import loaders

deliveries = clean.prepare(loaders.load_deliveries())
deliveries.groupby("over")["runs_off_bat"].mean()
```

## Data

| | |
|---|---|
| Source | [cricsheet.org/downloads/ipl_csv2.zip](https://cricsheet.org/downloads/ipl_csv2.zip) |
| Size | 6.8 MB zipped, 295,732 rows × 27 columns |
| Coverage | 1,243 matches, 19 seasons, 2008-04-18 to 2026-05-31 |
| Licence | Cricsheet's own — **not** covered by this repo's MIT licence |

The archive is **not committed**. It caches to `~/.cache/scorebook/`, outside the repo.
([ADR 0001](docs/decisions/0001-data-is-downloaded.md))

`data/sample_deliveries.csv` (458 rows, 63 KB) **is** committed, so a fresh clone runs
offline. It holds two matches, chosen deliberately rather than randomly: the first IPL
match ever played and the most recent one in the archive. Between them they carry both
season formats and both generations of team names — a random sample would contain neither.
Regenerate with `python scripts/make_sample.py`.

Memory, measured across all four combinations: all 27 columns as `object` is **227 MiB**;
the 16 in `USED_COLUMNS` as `object` is **159 MiB**; all 27 as `category` is **90 MiB**; the
16 as `category` is **21 MiB** — which is what `load_deliveries()` gives you.

So `usecols` alone buys 1.4× and the `category` dtype alone buys 2.5×, for 10.6× together.
The dtype is the bigger lever, not the column count — the opposite of the usual advice. It
also has a cost that is not memory, which is trap 4.

## Layout

```
src/scorebook/
├── data/schemas.py    every assumption about the file's shape, in one place
├── data/loaders.py    download, cache, and read one member out of the zip
├── clean.py           definitional fixes only — no analytical choices
├── describe.py        row/match/season counts and the null profile
├── plots.py           figure styling and saving; no chart builders
└── cli.py             scorebook fetch | describe

docs/questions.md      the five hypotheses, written first
docs/results.md        findings — a stub until you fill it
docs/decisions/        six ADRs, each with its cost
notebooks/             where the analysis goes
scripts/make_sample.py regenerates the committed sample
```

## Testing

```bash
pytest                          # 64 tests, offline, ~5 seconds
pytest --cov                    # 99%, gate is 90
pytest -m integration           # downloads and parses the real archive
ruff check . && pyright         # lint and types
```

Unit tests never touch the network, and that is **enforced**, not merely intended: a
conftest fixture fails any unmarked test that opens an HTTP connection. It exists because
a CLI test quietly downloaded the real 6.8 MB archive during development — it had no
cached copy to find, so it fetched one, and it passed. Discipline did not catch that.

`file://` URLs are still permitted, so the download tests exercise the real urllib path
against a fixture in `tmp_path`.

## Known limits

- **The `_info.csv` files are unused.** The archive holds 1,243 metadata files with toss,
  winner, and player-of-match. They are key-value long format, not tabular — `read_csv`
  returns nonsense without a pivot. Question 4 needs them, so question 4 may be deferred.
- **No model.** Pure EDA. A model would be v1.1, and nothing here would need restructuring
  to add one.
- **Seasons are not directly comparable.** CSK and RR were suspended in 2016–17; 2009 was
  played in South Africa and 2020 in the UAE. Any cross-season claim needs to say so.
- **`actual_delivery` is unused** rather than understood. Worth resolving upstream.

## Documentation

| File | What it covers |
|---|---|
| [docs/questions.md](docs/questions.md) | the five hypotheses, committed before analysis |
| [docs/data-dictionary.md](docs/data-dictionary.md) | all 27 columns, measured null rates |
| [docs/glossary.md](docs/glossary.md) | cricket terms, and the real names of these charts |
| [docs/architecture.md](docs/architecture.md) | how the pieces fit and why the split exists |
| [docs/results.md](docs/results.md) | findings |
| [docs/decisions/](docs/decisions/) | six ADRs |

## Licence

MIT — see [LICENSE](LICENSE). This covers the code only. The data is Cricsheet's and
carries its own terms.
