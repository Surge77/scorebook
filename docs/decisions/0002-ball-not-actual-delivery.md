# 0002 — Use `ball`, not the undocumented `actual_delivery`

**Status:** accepted

## Context

`all_matches.csv` ships 27 columns. Cricsheet's bundled `README.txt` documents 22 of them.
Five are undocumented: `actual_delivery`, `non_boundary`, `fielder_1`, `fielder_2`,
`fielder_3`.

Two of the 27 look like they mean the same thing, and they do not agree:

```
ball != actual_delivery   in  35,647 of 295,732 rows  (12.05%)
```

Every per-over aggregate in this project depends on getting the over number out of one of
them. Q1 (do runs spike in the death overs?) and Q5 (are wides getting rarer?) are both
wrong if the wrong column is used.

12.05% is suspiciously close to the rate of extras in the data, which suggests one column
counts re-bowled deliveries and the other does not. **That is a guess, and it was not
verified.**

## Decision

Use `ball`. Derive `over = floor(ball)` in `clean.add_over`. Do not load
`actual_delivery` at all, and record here that its meaning is unresolved.

## Why

**Only `ball` is specified.** Cricsheet's README says, verbatim: *"`ball` is a combination
of the over and delivery. For example, `0.3` represents the 3rd ball of the 1st over."*
That is an unambiguous contract from the publisher.

**`actual_delivery` has no contract at all.** It appears in the file and nowhere in the
documentation. Building the project's central derived column on an undocumented field means
an upstream change could alter its meaning without any signal, and every number in the repo
would shift with no test failing.

**A documented column that might be less precise beats an undocumented one that might be
more precise.** If `actual_delivery` turns out to be the better choice, switching is a
one-line change in `clean.add_over` plus one entry in `USED_COLUMNS`. Being wrong in the
direction of the documented field is cheap to reverse; being wrong in the direction of an
unspecified field is not even detectable.

## Cost

If `actual_delivery` is in fact the correct field for counting legal deliveries, then
per-over aggregates here are subtly off on 12% of rows, and the error is not random — it
concentrates in overs containing extras, which correlates with the death overs Q1 is about.

That is a real exposure and it is not resolved. Two things bound it:

- `over` is only ever used to *group* deliveries, never to count them. Grouping is robust
  to the disagreement as long as both columns share the same integer part, which is the
  likely case if they differ only in delivery numbering within an over. Not verified.
- README "Known limits" names this openly rather than burying it.

The proper fix is to ask Cricsheet what `actual_delivery` means, or to reconstruct it from
the per-match files and compare. Until then this is a documented unknown, not a solved
problem.
