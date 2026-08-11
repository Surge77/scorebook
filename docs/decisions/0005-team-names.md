# 0005 — Canonicalise renamed franchises; leave defunct ones alone

**Status:** accepted

## Context

`batting_team` holds **19 distinct names** across 19 seasons, for roughly 14 franchises:

| Name | Seasons | Span |
|---|---:|---|
| Mumbai Indians | 19 | 2008–2026 |
| Kolkata Knight Riders | 19 | 2008–2026 |
| Chennai Super Kings | 17 | 2008–2026 |
| Rajasthan Royals | 17 | 2008–2026 |
| Royal Challengers Bangalore | 16 | 2008–2023 |
| Kings XI Punjab | 13 | 2008–2020/21 |
| Delhi Daredevils | 11 | 2008–2018 |
| Delhi Capitals | 8 | 2019–2026 |
| Punjab Kings | 6 | 2021–2026 |
| Sunrisers Hyderabad | 14 | 2013–2026 |
| Deccan Chargers | 5 | 2008–2012 |
| Gujarat Titans | 5 | 2022–2026 |
| Lucknow Super Giants | 5 | 2022–2026 |
| Royal Challengers Bengaluru | 3 | 2024–2026 |
| Pune Warriors | 3 | 2011–2013 |
| Gujarat Lions | 2 | 2016–2017 |
| Rising Pune Supergiants | 1 | 2016 |
| Rising Pune Supergiant | 1 | 2017 |
| Kochi Tuskers Kerala | 1 | 2011 |

Grouped as-is, one franchise appears as two teams with disjoint histories, and every
per-team aggregate is wrong.

## Decision

Map four names onto their current form in `clean.TEAM_RENAMES`:

```
Royal Challengers Bangalore  -> Royal Challengers Bengaluru
Delhi Daredevils             -> Delhi Capitals
Kings XI Punjab              -> Punjab Kings
Rising Pune Supergiants      -> Rising Pune Supergiant
```

Leave every defunct franchise untouched. In particular, do **not** map Deccan Chargers onto
Sunrisers Hyderabad.

## Why

**The first three are the same franchise under a new name.** Same owners, same city, same
continuous entity. Bangalore's rename to Bengaluru in 2024 tracked the city's own official
renaming. Splitting them would mean RCB has two separate 16-season and 3-season histories,
which is simply false.

**`Rising Pune Supergiants` and `Rising Pune Supergiant` differ by one letter** and cover
consecutive seasons of a franchise that only ever existed for two. Whether that was an
official rename or an upstream correction does not matter: it is one team, and left alone it
becomes two teams with one season each — which then looks like a franchise that played once
and vanished, twice.

**Deccan Chargers is genuinely not Sunrisers Hyderabad.** The Deccan Chargers franchise was
terminated in 2012, and Sunrisers Hyderabad was awarded as a *new* franchise in 2013 to
different owners. They share a city and nothing else. Mapping them would fabricate a
continuous 2008–2026 Hyderabad history that never existed, and would silently attribute
Deccan's record to a team that did not play those matches.

This is the whole point of the ADR: the rule is not "collapse names that look similar", it
is "collapse names that refer to the same entity". Those come apart, and the second one
requires knowing the sport.

## Cost

**The map is hand-maintained.** A future rename needs a new entry, and nothing detects the
omission — a new name simply appears as a new team. Mitigated only by the count being small
and renames being newsworthy.

**Canonicalising loses the historical name.** After `clean.prepare()` there is no way to ask
"what was this team called in 2015?". Accepted because no question in `docs/questions.md`
needs it; if one ever does, the fix is to keep the original in a `team_name_as_played`
column rather than to stop canonicalising.

**Mapping onto the *current* name means the canonical value changes if a team renames
again.** Any chart or table checked into a document would then disagree with newly generated
output. `reports/` is gitignored partly for this reason.

**The `category` dtype has to be dropped and rebuilt** to remap values pandas has not seen,
so `canonical_teams` costs one full pass over the column. Measured as negligible at this
size, and `tests/test_clean.py` asserts the dtype survives — a silent downgrade to `object`
would quietly cost the memory saving the loader worked for.
