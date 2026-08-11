"""Cleaning steps. The season-year tests encode the trap that makes this module exist."""

from __future__ import annotations

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from scorebook import clean
from scorebook.data import schemas


def frame_from(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def season_frame(pairs: list[tuple[str, str]]) -> pd.DataFrame:
    """(season label, start_date) pairs — the only two columns add_season_year reads."""
    return frame_from([{"season": season, "start_date": date} for season, date in pairs])


# --- teams ---------------------------------------------------------------------------


def test_renames_collapse_onto_the_current_name():
    frame = frame_from([
        {"batting_team": "Royal Challengers Bangalore", "bowling_team": "Delhi Daredevils"},
        {"batting_team": "Kings XI Punjab", "bowling_team": "Mumbai Indians"},
    ])
    out = clean.canonical_teams(frame)
    assert out["batting_team"].tolist() == ["Royal Challengers Bengaluru", "Punjab Kings"]
    assert out["bowling_team"].tolist() == ["Delhi Capitals", "Mumbai Indians"]


def test_the_one_letter_rename_collapses():
    """Rising Pune Supergiants (2016) and Rising Pune Supergiant (2017) are one franchise
    across its only two seasons. Left alone, every per-team aggregate splits it in two."""
    frame = frame_from([
        {"batting_team": "Rising Pune Supergiants", "bowling_team": "Gujarat Lions"},
        {"batting_team": "Rising Pune Supergiant", "bowling_team": "Gujarat Lions"},
    ])
    out = clean.canonical_teams(frame)
    assert out["batting_team"].nunique() == 1


def test_defunct_franchises_are_not_merged_into_successors():
    """Sunrisers Hyderabad was a new franchise, not a Deccan Chargers rebrand. Merging
    them would invent a continuous history.

    Asserts the whole DEFUNCT_TEAMS set rather than one name, so that constant documents a
    real invariant instead of sitting there unused.
    """
    overlap = clean.DEFUNCT_TEAMS & clean.TEAM_RENAMES.keys()
    assert not overlap, f"defunct franchises must not be renamed away: {overlap}"

    frame = frame_from([{"batting_team": "Deccan Chargers", "bowling_team": "Pune Warriors"}])
    out = clean.canonical_teams(frame)
    assert out["batting_team"].tolist() == ["Deccan Chargers"]
    assert out["bowling_team"].tolist() == ["Pune Warriors"]


def test_canonical_teams_preserves_category_dtype():
    """Renaming must not silently cost the dtype that keeps the real frame at 89 MiB."""
    frame = frame_from([{"batting_team": "Kings XI Punjab", "bowling_team": "Mumbai Indians"}])
    frame["batting_team"] = frame["batting_team"].astype("category")
    out = clean.canonical_teams(frame)
    assert str(out["batting_team"].dtype) == "category"
    assert out["batting_team"].tolist() == ["Punjab Kings"]


def test_canonical_teams_tolerates_a_missing_team_column():
    out = clean.canonical_teams(frame_from([{"batting_team": "Kings XI Punjab"}]))
    assert out["batting_team"].tolist() == ["Punjab Kings"]


def test_canonical_teams_does_not_mutate_its_argument():
    frame = frame_from([{"batting_team": "Kings XI Punjab", "bowling_team": "Mumbai Indians"}])
    clean.canonical_teams(frame)
    assert frame["batting_team"].tolist() == ["Kings XI Punjab"]


# --- season year ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "season, start_date, expected",
    [
        # The second part of the slash is right here...
        ("2007/08", "2008-04-18", 2008),
        ("2009/10", "2010-03-12", 2010),
        # ...and wrong here. IPL 2020/21 was played entirely in 2020.
        ("2020/21", "2020-09-19", 2020),
        # And the first part of the slash would map 2009/10 onto the separate, genuine
        # 2009 season, silently merging two of them.
        ("2009", "2009-04-18", 2009),
        ("2026", "2026-03-28", 2026),
    ],
)
def test_season_year_comes_from_the_date_not_the_label(season, start_date, expected):
    out = clean.add_season_year(season_frame([(season, start_date)]))
    assert out["season_year"].tolist() == [expected]


def test_slash_seasons_do_not_collide_with_plain_ones():
    """The bug this guards: 2009 and 2009/10 are different seasons played a year apart."""
    out = clean.add_season_year(season_frame([
        ("2009", "2009-04-18"),
        ("2009/10", "2010-03-12"),
    ]))
    assert sorted(out["season_year"].tolist()) == [2009, 2010]


def test_a_season_spanning_two_years_is_refused_not_guessed():
    """If the IPL ever runs across New Year, the right move is to fail and make someone
    decide — not to silently pick a year."""
    with pytest.raises(clean.CleaningError, match="more than one calendar year"):
        clean.add_season_year(season_frame([
            ("2031/32", "2031-12-20"),
            ("2031/32", "2032-01-10"),
        ]))


def test_implausible_years_are_refused():
    with pytest.raises(clean.CleaningError, match="outside the plausible"):
        clean.add_season_year(season_frame([("1999", "1999-04-18")]))


@pytest.mark.parametrize("missing", ["season", "start_date"])
def test_add_season_year_names_the_column_it_needs(missing):
    frame = season_frame([("2026", "2026-03-28")]).drop(columns=[missing])
    with pytest.raises(clean.CleaningError, match=missing):
        clean.add_season_year(frame)


@given(year=st.integers(min_value=2008, max_value=2099), month=st.integers(1, 12))
def test_season_year_always_matches_the_start_date_year(year: int, month: int):
    frame = season_frame([(f"{year}", f"{year}-{month:02d}-15")])
    assert clean.add_season_year(frame)["season_year"].tolist() == [year]


# --- over ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ball, expected_over",
    [(0.1, 0), (0.6, 0), (1.1, 1), (5.4, 5), (19.6, 19)],
)
def test_over_is_the_integer_part_of_ball(ball, expected_over):
    """Cricsheet: "0.3 represents the 3rd ball of the 1st over"."""
    out = clean.add_over(frame_from([{"ball": ball}]))
    assert out["over"].tolist() == [expected_over]


def test_over_handles_a_re_bowled_over_past_six_deliveries():
    """Wides and no-balls are re-bowled, so an over can hold more than six rows. All of
    them still belong to the same over."""
    out = clean.add_over(frame_from([{"ball": b} for b in (4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7)]))
    assert out["over"].nunique() == 1
    assert len(out) > schemas.BALLS_PER_OVER


def test_add_over_needs_a_ball_column():
    with pytest.raises(clean.CleaningError, match="ball"):
        clean.add_over(frame_from([{"innings": 1}]))


# --- nulls ---------------------------------------------------------------------------


def test_extras_nulls_become_zero():
    """A null in `wides` means no wide was bowled. Left null, the row drops out of sums."""
    frame = frame_from([{"wides": 1.0, "noballs": None}, {"wides": None, "noballs": None}])
    out = clean.fill_extras(frame)
    assert out["wides"].tolist() == [1, 0]
    assert out["noballs"].tolist() == [0, 0]
    assert out["wides"].sum() == 1


def test_wicket_type_nulls_survive_cleaning():
    """"No wicket" is not a dismissal type. Inventing a "none" category would show up in
    every value_counts as the overwhelming winner."""
    frame = frame_from([
        {"ball": 0.1, "wicket_type": None, "season": "2026", "start_date": "2026-03-28",
         "batting_team": "Mumbai Indians", "bowling_team": "Punjab Kings"},
        {"ball": 0.2, "wicket_type": "caught", "season": "2026", "start_date": "2026-03-28",
         "batting_team": "Mumbai Indians", "bowling_team": "Punjab Kings"},
    ])
    out = clean.prepare(frame)
    assert out["wicket_type"].isna().sum() == 1
    assert out["wicket_type"].dropna().tolist() == ["caught"]


# --- the categorical groupby trap ----------------------------------------------------


def category_frame() -> pd.DataFrame:
    frame = frame_from([
        {"batting_team": "Mumbai Indians", "season_year": 2026, "runs_off_bat": 4},
        {"batting_team": "Mumbai Indians", "season_year": 2026, "runs_off_bat": 2},
        {"batting_team": "Deccan Chargers", "season_year": 2012, "runs_off_bat": 6},
    ])
    frame["batting_team"] = frame["batting_team"].astype("category")
    return frame


def test_filtering_a_category_leaves_phantom_groups():
    """Pins the trap `drop_unused_categories` exists for, so it cannot change unnoticed.

    A category column keeps its full value list after a filter, and groupby defaults to
    observed=False — so a team that did not play still appears, scoring 0.
    """
    recent = category_frame()
    recent = recent[recent["season_year"] == 2026]
    assert recent["batting_team"].nunique() == 1, "only one team actually played"

    grouped = recent.groupby("batting_team", observed=False)["runs_off_bat"].sum()
    assert len(grouped) == 2, "the defunct team is still a category, so it still gets a row"
    assert grouped["Deccan Chargers"] == 0, "reported as zero runs rather than omitted"


def test_drop_unused_categories_removes_the_phantom_groups():
    recent = category_frame()
    recent = clean.drop_unused_categories(recent[recent["season_year"] == 2026])

    grouped = recent.groupby("batting_team", observed=False)["runs_off_bat"].sum()
    assert list(grouped.index) == ["Mumbai Indians"]
    assert grouped["Mumbai Indians"] == 6


def test_observed_true_also_fixes_the_row_count():
    """The more direct habit, documented alongside the helper."""
    recent = category_frame()
    recent = recent[recent["season_year"] == 2026]
    grouped = recent.groupby("batting_team", observed=True)["runs_off_bat"].sum()
    assert list(grouped.index) == ["Mumbai Indians"]


def test_drop_unused_categories_preserves_dtype_and_values():
    """It must not quietly cost the 4.6x memory saving the category dtype buys."""
    out = clean.drop_unused_categories(category_frame())
    assert str(out["batting_team"].dtype) == "category"
    assert out["batting_team"].tolist() == ["Mumbai Indians", "Mumbai Indians", "Deccan Chargers"]


def test_drop_unused_categories_leaves_non_categorical_columns_alone():
    out = clean.drop_unused_categories(category_frame())
    assert out["runs_off_bat"].tolist() == [4, 2, 6]
    assert out["season_year"].tolist() == [2026, 2026, 2012]


def test_drop_unused_categories_does_not_mutate_its_argument():
    frame = category_frame()
    subset = frame[frame["season_year"] == 2026]
    clean.drop_unused_categories(subset)
    assert len(subset["batting_team"].cat.categories) == 2, "argument left untouched"


def test_always_empty_columns_are_dropped():
    frame = frame_from([{"ball": 0.1, "penalty": None, "fielder_3": None}])
    out = clean.drop_always_empty(frame)
    assert "penalty" not in out.columns
    assert "fielder_3" not in out.columns
    assert "ball" in out.columns


def test_drop_always_empty_ignores_absent_columns():
    frame = frame_from([{"ball": 0.1}])
    assert list(clean.drop_always_empty(frame).columns) == ["ball"]


# --- pipeline ------------------------------------------------------------------------


def test_prepare_runs_every_step(sample_csv):
    from scorebook.data import loaders

    out = clean.prepare(loaders.load_sample(sample_csv))
    assert {"over", "season_year"} <= set(out.columns)
    assert out["season_year"].tolist() == [2026, 2026, 2026, 2008]
    assert out["over"].tolist() == [0, 0, 1, 0]
    # Bangalore -> Bengaluru and Kings XI Punjab -> Punjab Kings both applied.
    assert "Royal Challengers Bengaluru" in out["batting_team"].tolist()
    assert "Punjab Kings" in out["bowling_team"].tolist()
    assert out["wides"].tolist() == [0, 1, 0, 0]
