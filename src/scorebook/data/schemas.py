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

# Columns loaded by default. Measured: all 27 with category dtypes is 107 MiB, these 16
# are 38 MiB, and a naive all-object read of all 27 is 244 MiB. So the two levers are
# worth 2.3x (dtypes) and 2.8x (usecols) respectively, 6.4x together.
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
# `season` is included because it is a *string* upstream (see clean.season_to_year).
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

# Deliveries per over in a completed over. Used to sanity-check derived over numbers;
# an over can contain more rows than this because wides and no-balls are re-bowled.
BALLS_PER_OVER = 6


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
