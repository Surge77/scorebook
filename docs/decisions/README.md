# Architecture decision records

Short notes on decisions that are not obvious from the code, written at the
time so the reasoning survives.

Each records the situation, what was chosen, and what it cost. A decision with
no downside listed is usually one that was not thought about hard enough.

| # | Decision |
| --- | --- |
| [0001](0001-data-is-downloaded.md) | Download the archive on demand instead of committing it |
| [0002](0002-ball-not-actual-delivery.md) | Use `ball` rather than the undocumented `actual_delivery` |
| [0003](0003-informative-nulls.md) | Treat three kinds of null three different ways |
| [0004](0004-season-year.md) | Derive the season year from `start_date`, never from the season label |
| [0005](0005-team-names.md) | Canonicalise renamed franchises; leave defunct ones alone |
| [0006](0006-analysis-in-notebooks.md) | Keep the analysis out of the package |
