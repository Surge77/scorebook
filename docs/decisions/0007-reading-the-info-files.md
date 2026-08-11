# 0007 — Read the info files into a second frame

**Status:** accepted

## Context

`all_matches.csv` has no result. It records every delivery of all 1,243 matches and never
says who won any of them, so Q4 — which venue shows the largest home advantage — was
scoped without checking whether the loaded data could answer it. It could not.

The outcomes are in the archive, in 1,243 `<match_id>_info.csv` members that nothing read.
They are not tabular. Each line is `info,<key>,<value>`, with a fourth field on some rows:

```
version,2.3.0
info,team,Sunrisers Hyderabad
info,team,Royal Challengers Bangalore
info,date,2017/04/05
info,venue,"Rajiv Gandhi International Stadium, Uppal"
info,toss_winner,Royal Challengers Bangalore
info,winner,Sunrisers Hyderabad
info,winner_runs,35
info,player,Sunrisers Hyderabad,DA Warner
```

`read_csv` on that returns three unnamed columns of mixed meaning — a venue and a player
name stacked in the same column — which is the sense in which it "returns nonsense".

## Decision

`loaders.load_match_info()` pivots the 1,243 members into one row per match, returning
`schemas.INFO_COLUMNS`, joinable to the deliveries on `match_id`. It is a **separate
frame**, not a merge into the delivery frame, and it is a **separate call**, not part of
`load_deliveries`.

Repeated keys take their first value. `team` is the exception and widens into
`team_1`/`team_2`. `player`, `registry` and the four official columns are dropped.

## Why

**This is acquisition, not analysis, so it belongs in the package.** ADR 0006 keeps
aggregation out; reading a documented file into the shape it describes is the same kind of
work `load_deliveries` already does. Who won is a fact in the archive, not a claim.

**A separate frame, because the grain is different.** The deliveries frame is one row per
ball; this is one row per match. Merging would repeat every match's metadata across ~238
delivery rows, inflate memory for the majority of analyses that never ask about outcomes,
and make `match_id` stop being the obvious join key. Two frames and an explicit join say
what is happening.

**A separate call, because the cost is real.** It opens 1,243 zip members. Folding that
into `load_deliveries` would put it on the path of every notebook, including the four
questions that do not need it.

**`player` and `registry` are dropped on grain, not on interest.** A single file holds 22
`player` rows and around 50 `registry` rows. Folding them in multiplies the row count by
~70 and the result is no longer one row per match. A squad or player-identity frame is a
separate loader whenever something needs one.

**`winner` is left null on the 25 matches without one**, joining the family in ADR 0003.
The nulls decompose as 16 ties and 9 no-results — and the 16 ties *were* decided, by super
over, with the victor in `eliminator`. So `outcome` and `eliminator` are both returned and
neither is folded into `winner`: whether a super-over win counts as a win is an analytical
choice, and this module does not get to make it.

## Cost

**Two formats in one archive, and now two date constants.** The info files write
`2017/04/05`; `all_matches.csv` writes `2008-04-18`. Nothing upstream documents the
difference. `INFO_DATE_FORMAT` sits beside `DATE_FORMAT` in `schemas.py` and the two must
not be confused — parsing either with the other's format raises on every row, which is at
least loud.

**Team names arrive raw and must be canonicalised by the caller.** `canonical_teams` grew
a `columns` argument for this. Forget it and Delhi Daredevils and Delhi Capitals appear as
two franchises in a winner table, which is exactly the failure ADR 0005 exists to prevent —
now reachable through a second door.

**1,243 members are parsed on every call, with no caching.** It takes a few seconds and
allocates a small frame. Memoising would be easy and is deliberately not done: there is one
caller, and a cache that can go stale against a re-downloaded archive is a worse bug than
a few seconds.

**`INFO_IGNORED_KEYS` is an allowlist maintained by hand.** A new upstream key is silently
dropped rather than surfacing. This is the same exposure `validate_columns` accepts for the
delivery file, where `actual_delivery` appeared unannounced — tolerating additions is what
keeps the loader working when Cricsheet adds a field, and the price is not noticing.
