"""Cleaning steps that are definitional, not analytical.

The line this module holds: it derives things the data already means but does not state
(the over number is inside `ball`; the season year is inside `start_date`), and it
normalises names that refer to the same thing. It does not decide anything an analyst
should defend — there is deliberately no `phase` column here, because where the death
overs begin is an argument, not a fact.

Every function returns a new frame. Nothing mutates its argument.
"""

from __future__ import annotations

import pandas as pd

from .data import schemas

# Franchises that changed name. Mapped to the most recent name so a cross-season groupby
# does not split one team into two.
#
# "Rising Pune Supergiants" (2016) and "Rising Pune Supergiant" (2017) differ by one
# letter and are the same franchise across its only two seasons. Whether that was an
# official rename or an upstream correction does not change the handling.
TEAM_RENAMES: dict[str, str] = {
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Delhi Daredevils": "Delhi Capitals",
    "Kings XI Punjab": "Punjab Kings",
    "Rising Pune Supergiants": "Rising Pune Supergiant",
}

# Franchises that ended. Deliberately absent from TEAM_RENAMES: Sunrisers Hyderabad was
# a new franchise awarded after Deccan Chargers was terminated, not a rebrand of it.
# Merging them would fabricate a continuous history that does not exist.
# See docs/decisions/0005-team-names.md.
DEFUNCT_TEAMS: frozenset[str] = frozenset({
    "Deccan Chargers",
    "Pune Warriors",
    "Kochi Tuskers Kerala",
    "Gujarat Lions",
    "Rising Pune Supergiant",
})

TEAM_COLUMNS: tuple[str, ...] = ("batting_team", "bowling_team")

# The same franchises appear under different column names in the match info frame, where
# a team can be a participant, the toss winner, or the match winner.
INFO_TEAM_COLUMNS: tuple[str, ...] = ("team_1", "team_2", "toss_winner", "winner")

# Grounds written more than one way. Cricsheet does not normalise venue names, so the
# archive holds 60 venue strings for 36 grounds: a city suffix appears and disappears
# ("Eden Gardens" / "Eden Gardens, Kolkata"), punctuation varies ("M.Chinnaswamy"), and
# some grounds were genuinely renamed mid-league. Mapped to the current name, exactly as
# TEAM_RENAMES is, because the alternative is one ground counted as three.
#
# Chepauk is the worst case: 48 matches under one spelling and 41 under another, split
# almost exactly at 2016. Group by the raw string and Chennai appear to have abandoned
# their own ground halfway through the league.
VENUE_RENAMES: dict[str, str] = {
    # City suffix present in some seasons and absent in others.
    "Eden Gardens, Kolkata": "Eden Gardens",
    "Wankhede Stadium, Mumbai": "Wankhede Stadium",
    "Brabourne Stadium, Mumbai": "Brabourne Stadium",
    "Dr DY Patil Sports Academy, Mumbai": "Dr DY Patil Sports Academy",
    "Sawai Mansingh Stadium, Jaipur": "Sawai Mansingh Stadium",
    "M Chinnaswamy Stadium, Bengaluru": "M Chinnaswamy Stadium",
    "Himachal Pradesh Cricket Association Stadium, Dharamsala":
        "Himachal Pradesh Cricket Association Stadium",
    "Shaheed Veer Narayan Singh International Stadium, Raipur":
        "Shaheed Veer Narayan Singh International Stadium",
    "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium, Visakhapatnam":
        "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium",
    "MA Chidambaram Stadium, Chepauk": "MA Chidambaram Stadium",
    "MA Chidambaram Stadium, Chepauk, Chennai": "MA Chidambaram Stadium",
    "Rajiv Gandhi International Stadium, Uppal": "Rajiv Gandhi International Stadium",
    "Rajiv Gandhi International Stadium, Uppal, Hyderabad":
        "Rajiv Gandhi International Stadium",
    "Maharashtra Cricket Association Stadium, Pune": "Maharashtra Cricket Association Stadium",
    "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur":
        "Maharaja Yadavindra Singh International Cricket Stadium",
    "Maharaja Yadavindra Singh International Cricket Stadium, New Chandigarh":
        "Maharaja Yadavindra Singh International Cricket Stadium",
    # Punctuation only.
    "M.Chinnaswamy Stadium": "M Chinnaswamy Stadium",
    # Genuine renames. Mapped forward to the current name.
    "Feroz Shah Kotla": "Arun Jaitley Stadium",
    "Arun Jaitley Stadium, Delhi": "Arun Jaitley Stadium",
    "Punjab Cricket Association Stadium, Mohali":
        "Punjab Cricket Association IS Bindra Stadium",
    "Punjab Cricket Association IS Bindra Stadium, Mohali":
        "Punjab Cricket Association IS Bindra Stadium",
    "Punjab Cricket Association IS Bindra Stadium, Mohali, Chandigarh":
        "Punjab Cricket Association IS Bindra Stadium",
    "Sardar Patel Stadium, Motera": "Narendra Modi Stadium",
    "Narendra Modi Stadium, Ahmedabad": "Narendra Modi Stadium",
    "Sheikh Zayed Stadium": "Zayed Cricket Stadium",
    "Zayed Cricket Stadium, Abu Dhabi": "Zayed Cricket Stadium",
    # Gahunje, renamed when the naming sponsor left. Same ground, both spellings.
    "Subrata Roy Sahara Stadium": "Maharashtra Cricket Association Stadium",
}

VENUE_COLUMN = "venue"

# Sanity bounds for a derived season year. The IPL began in 2008; the upper bound only
# needs to catch a parsing accident, not predict the end of the league.
_MIN_SEASON_YEAR = 2008
_MAX_SEASON_YEAR = 2100


class CleaningError(ValueError):
    """An assumption this module relies on no longer holds in the data."""


def canonical_teams(
    frame: pd.DataFrame, columns: tuple[str, ...] = TEAM_COLUMNS
) -> pd.DataFrame:
    """Collapse renamed franchises onto their current name, in the given team columns.

    Defaults to the two columns of the deliveries frame. The match info frame names the
    same franchises differently, so pass `INFO_TEAM_COLUMNS` for that one — a match won
    by "Delhi Daredevils" and one won by "Delhi Capitals" are the same franchise, and
    counting them apart is how a home-advantage table ends up with two half-teams.
    """
    out = frame.copy()
    for column in columns:
        if column not in out.columns:
            continue
        series = out[column]
        # A categorical has to lose its dtype before an arbitrary remap, then regain it,
        # or unseen replacement values raise.
        if isinstance(series.dtype, pd.CategoricalDtype):
            out[column] = series.astype("string").replace(TEAM_RENAMES).astype("category")
        else:
            out[column] = series.replace(TEAM_RENAMES)
    return out


def canonical_venues(frame: pd.DataFrame, column: str = VENUE_COLUMN) -> pd.DataFrame:
    """Collapse the spellings of one ground onto its current name.

    The same fix as `canonical_teams`, for the same reason: 60 venue strings describe 36
    grounds, and grouping by the raw string reports one ground as several — each with a
    fraction of its matches, and each looking like a small sample.
    """
    out = frame.copy()
    if column not in out.columns:
        return out
    series = out[column]
    if isinstance(series.dtype, pd.CategoricalDtype):
        out[column] = series.astype("string").replace(VENUE_RENAMES).astype("category")
    else:
        out[column] = series.replace(VENUE_RENAMES)
    return out


def add_season_year(frame: pd.DataFrame) -> pd.DataFrame:
    """Add `season_year`: the calendar year a season was actually played in.

    Derived from `start_date`, never parsed out of the `season` label, because no rule
    over that string is correct. Cricsheet labels three seasons with a slash:

        2007/08 -> played 2008    (second part is right)
        2009/10 -> played 2010    (second part is right)
        2020/21 -> played 2020    (second part is WRONG)

    and taking the first part maps 2009/10 to 2009, which collides with the separate,
    genuine 2009 season and silently merges two of them.

    Every IPL season to date was played inside a single calendar year, so this raises if
    that ever stops being true rather than picking a year and hiding the ambiguity.
    See docs/decisions/0004-season-year.md.
    """
    for required in ("season", "start_date"):
        if required not in frame.columns:
            raise CleaningError(f"add_season_year needs a {required!r} column")

    out = frame.copy()
    dates = pd.to_datetime(out["start_date"])
    years = dates.dt.year

    spans = years.groupby(out["season"], observed=True).nunique()
    straddling = spans[spans > 1]
    if not straddling.empty:
        raise CleaningError(
            f"season(s) {list(straddling.index)} span more than one calendar year, "
            "so a single season_year is ambiguous. Decide the rule explicitly in "
            "docs/decisions/0004-season-year.md before continuing."
        )

    low, high = int(years.min()), int(years.max())
    if not _MIN_SEASON_YEAR <= low <= high <= _MAX_SEASON_YEAR:
        raise CleaningError(
            f"derived season years span {low}-{high}, outside the plausible "
            f"{_MIN_SEASON_YEAR}-{_MAX_SEASON_YEAR} range; check start_date parsing."
        )

    out["season_year"] = years.astype("int16")
    return out


def add_over(frame: pd.DataFrame) -> pd.DataFrame:
    """Add a zero-indexed `over` number from `ball`.

    Cricsheet documents `ball` as "a combination of the over and delivery", where 0.3 is
    the third ball of the first over — so the over is the integer part.

    Uses `ball`, not the undocumented `actual_delivery`. The two disagree on 12.05% of
    rows and only `ball` is specified upstream.
    See docs/decisions/0002-ball-not-actual-delivery.md.
    """
    if "ball" not in frame.columns:
        raise CleaningError("add_over needs a 'ball' column")
    out = frame.copy()
    # floordiv(1) rather than numpy.floor: pandas-native, so numpy stays an
    # undeclared transitive dependency this package never imports directly.
    out["over"] = pd.to_numeric(out["ball"]).floordiv(1).astype("int16")
    return out


def fill_extras(frame: pd.DataFrame) -> pd.DataFrame:
    """Replace nulls in the extras columns with 0.

    A null in `wides` means no wide was bowled, not that nobody recorded it — so 0 is the
    true value and leaving it null would drop the row from any sum.

    `wicket_type` and `player_dismissed` are pointedly NOT filled. "No wicket" is not a
    dismissal type, and inventing a "none" category would poison every value_counts.
    See docs/decisions/0003-informative-nulls.md.
    """
    out = frame.copy()
    for column in schemas.EXTRAS_COLUMNS:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column]).fillna(0).astype("int16")
    return out


def drop_unused_categories(frame: pd.DataFrame) -> pd.DataFrame:
    """Forget category values that no longer occur in the frame. **Call this after every
    filter, before grouping.**

    Category dtypes carry their full value list independently of the rows present, and
    `groupby` on a categorical defaults to `observed=False` — it emits one row per *category*,
    not per value present. So filtering to 2026 and grouping by team returns 15 rows for the
    10 teams that played, with Deccan Chargers and four other defunct franchises reported as
    0 runs. No error, no warning about the extra rows: just five wrong rows in an answer.

        recent = deliveries[deliveries.season_year == 2026]
        recent = clean.drop_unused_categories(recent)
        recent.groupby("batting_team", observed=True)["runs_off_bat"].sum()

    Passing `observed=True` fixes the row count on its own and is the more direct habit;
    this function is for when the frame is handed to code that will not. Both are worth
    doing. pandas 3.0 makes `observed=True` the default, at which point this becomes
    unnecessary — until then, the 7.4x memory saving that category dtypes buy comes with
    this string attached.
    """
    out = frame.copy()
    for column in out.columns:
        if isinstance(out[column].dtype, pd.CategoricalDtype):
            out[column] = out[column].cat.remove_unused_categories()
    return out


def drop_always_empty(frame: pd.DataFrame) -> pd.DataFrame:
    """Drop the columns that are empty in every IPL row.

    They are structurally empty — the format is shared with other competitions — so they
    carry no information, unlike the columns in INFORMATIVE_NULLS.
    """
    present = [column for column in frame.columns if column in schemas.ALWAYS_EMPTY]
    return frame.drop(columns=present)


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    """The whole cleaning pipeline, in dependency order.

    This is what the notebook calls. Each step is public and independently testable so a
    reader can see what was done to the data rather than trusting one opaque function.
    """
    return (
        frame.pipe(drop_always_empty)
        .pipe(canonical_teams)
        .pipe(canonical_venues)
        .pipe(add_season_year)
        .pipe(add_over)
        .pipe(fill_extras)
    )
