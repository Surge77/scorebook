"""The Cricsheet column contract.

Every fact this package assumes about the shape of `all_matches.csv` lives here, so a
change upstream fails in one place with a useful message instead of surfacing as a wrong
number three notebooks later.

Measured against the archive downloaded 2026-08-11: 295,732 rows, 27 columns, 1,243
matches, 19 seasons (2007/08 to 2026).
"""

from __future__ import annotations

# Every column the archive actually ships, in file order.
#
# Cricsheet's own README documents only 22 of these. The five undocumented ones are
# marked below; `actual_delivery` is the one that matters, and the reason this package
# uses `ball` instead. See docs/decisions/0002-ball-not-actual-delivery.md.
ALL_COLUMNS: tuple[str, ...] = (
    "match_id",
    "season",
    "start_date",
    "venue",
    "innings",
    "ball",
    "actual_delivery",       # undocumented upstream
    "batting_team",
    "bowling_team",
    "striker",
    "non_striker",
    "bowler",
    "runs_off_bat",
    "extras",
    "wides",
    "noballs",
    "byes",
    "legbyes",
    "penalty",
    "non_boundary",         # undocumented upstream
    "wicket_type",
    "player_dismissed",
    "other_wicket_type",
    "other_player_dismissed",
    "fielder_1",            # undocumented upstream
    "fielder_2",            # undocumented upstream
    "fielder_3",            # undocumented upstream
)

# Columns loaded by default. Measured: all 27 as object is 227 MiB, these 16 as object is
# 159 MiB, all 27 as category is 90 MiB, and these 16 as category is 21 MiB. So usecols is
# worth 1.4x on its own, the category dtype 2.5x, and the two together 10.6x.
# Anything genuinely needed later can be passed explicitly to load_deliveries().
USED_COLUMNS: tuple[str, ...] = (
    "match_id",
    "season",
    "start_date",
    "venue",
    "innings",
    "ball",
    "batting_team",
    "bowling_team",
    "striker",
    "bowler",
    "runs_off_bat",
    "extras",
    "wides",
    "noballs",
    "wicket_type",
    "player_dismissed",
)

# Low-cardinality text: 19 team names, 60 venues, 10 dismissal types across 295k rows.
# `season` is included because it is a *string* upstream — and stays one, because no rule
# over that string yields the right year (see clean.add_season_year, which reads
# start_date instead).
CATEGORICAL: frozenset[str] = frozenset({
    "season",
    "venue",
    "batting_team",
    "bowling_team",
    "striker",
    "bowler",
    "wicket_type",
    "player_dismissed",
})

# Empty in every one of the 295,732 IPL rows. They exist because the format is shared
# with other formats and competitions, not because IPL data is missing.
#
# These are safe to drop. The columns in INFORMATIVE_NULLS are not — that distinction
# is the whole point of docs/decisions/0003-informative-nulls.md.
ALWAYS_EMPTY: frozenset[str] = frozenset({
    "penalty",
    "non_boundary",
    "other_wicket_type",
    "other_player_dismissed",
    "fielder_3",
})

# Null here means "this did not happen on this delivery", never "unknown". Measured null
# rates: wicket_type 95.0%, wides 96.7%, noballs 99.6%, byes 99.7%, legbyes 98.5%.
#
# The numeric ones are filled with 0 by clean.fill_extras. `wicket_type` and
# `player_dismissed` are deliberately left null: "no wicket" is not a dismissal type,
# and inventing a "none" category would corrupt any value_counts over it.
INFORMATIVE_NULLS: frozenset[str] = frozenset({
    "wides",
    "noballs",
    "byes",
    "legbyes",
    "wicket_type",
    "player_dismissed",
})

# Extras columns filled with 0 rather than left null. Subset of INFORMATIVE_NULLS.
EXTRAS_COLUMNS: tuple[str, ...] = ("wides", "noballs", "byes", "legbyes")

# `start_date` is written as an ISO-8601 calendar date. Passing the format explicitly to
# to_datetime skips pandas' per-value format inference and, more importantly, makes a
# future upstream format change fail loudly instead of being silently re-inferred.
DATE_COLUMN = "start_date"
DATE_FORMAT = "%Y-%m-%d"

# Deliveries per over in a completed over. Used to sanity-check derived over numbers;
# an over can contain more rows than this because wides and no-balls are re-bowled.
BALLS_PER_OVER = 6


# --- the per-match metadata files -------------------------------------------------
#
# The archive also ships 1,243 `<match_id>_info.csv` members. They are not tabular: each
# line is `info,<key>,<value>[,<extra>]`, so read_csv returns three unnamed columns of
# mixed meaning rather than a match. loaders.load_match_info pivots them.
#
#     version,2.3.0
#     info,team,Sunrisers Hyderabad
#     info,team,Royal Challengers Bangalore
#     info,venue,"Rajiv Gandhi International Stadium, Uppal"
#     info,winner,Sunrisers Hyderabad
#     info,player,Sunrisers Hyderabad,DA Warner
#
# See docs/decisions/0007-reading-the-info-files.md.
INFO_MEMBER_SUFFIX = "_info.csv"

# Keys taken as a single value per match. Measured presence across all 1,243 files:
# venue, city, toss_winner, toss_decision 100%; player_of_match 99.3%; winner 98.0%;
# winner_wickets 53.1%; winner_runs 44.9%; outcome 2.0%; method 1.9%; eliminator 1.3%.
INFO_SCALAR_KEYS: tuple[str, ...] = (
    "match_id",
    "season",
    "venue",
    "city",
    "toss_winner",
    "toss_decision",
    "winner",
    "winner_runs",
    "winner_wickets",
    "outcome",
    "eliminator",
    "method",
    "player_of_match",
)

# Keys that repeat within one file. `team` appears exactly twice and is folded into
# team_1/team_2; `date` appears twice on the two matches that ran into a reserve day, and
# the first is the start. The rest are dropped: `player` alone is 22 rows per match and
# would multiply the grain by 22 for information no question here asks for.
INFO_TEAM_KEY = "team"
INFO_DATE_KEY = "date"
INFO_IGNORED_KEYS: frozenset[str] = frozenset({
    "player",
    "registry",
    "umpire",
    "reserve_umpire",
    "tv_umpire",
    "match_referee",
    "balls_per_over",
    "team_type",
    "gender",
    "event",
    "match_type",
    "match_number",
    "overs",
    "target_overs",
    "target_runs",
    "super_over",
})

# One row per match, in this order.
INFO_COLUMNS: tuple[str, ...] = (
    "match_id",
    "season",
    "start_date",
    "venue",
    "city",
    "team_1",
    "team_2",
    "toss_winner",
    "toss_decision",
    "winner",
    "winner_runs",
    "winner_wickets",
    "outcome",
    "eliminator",
    "method",
    "player_of_match",
)

# Text columns worth a category dtype in the info frame. `winner` is included even though
# it is nullable — a nullable category is fine, and "no winner" is exactly the kind of
# informative null docs/decisions/0003-informative-nulls.md is about.
INFO_CATEGORICAL: frozenset[str] = frozenset({
    "season",
    "venue",
    "city",
    "team_1",
    "team_2",
    "toss_winner",
    "toss_decision",
    "winner",
    "outcome",
    "eliminator",
    "method",
})

# The info files write dates with slashes, `2017/04/05`, where all_matches.csv writes
# `2008-04-18`. Two files in one archive, two formats, and nothing upstream says so —
# parsing an info date with DATE_FORMAT raises on every row.
INFO_DATE_FORMAT = "%Y/%m/%d"


class SchemaError(ValueError):
    """The archive does not have the columns this package was written against.

    Raised instead of letting pandas fail deep inside a groupby, because the useful
    message is "Cricsheet changed the format and here is what is missing", not
    "KeyError: 'ball'".
    """


def validate_columns(found: list[str], *, expected: tuple[str, ...] = USED_COLUMNS) -> None:
    """Check every expected column is present. Extra columns are fine — Cricsheet adds
    them without notice, which is exactly how `actual_delivery` appeared."""
    missing = [column for column in expected if column not in found]
    if missing:
        raise SchemaError(
            f"Cricsheet archive is missing {len(missing)} expected column(s): "
            f"{', '.join(missing)}. Found: {', '.join(sorted(found))}. "
            "The upstream format may have changed; update src/scorebook/data/schemas.py."
        )
