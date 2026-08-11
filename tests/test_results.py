"""The numbers quoted in docs/results.md, pinned against drift.

Every test here re-derives a figure that appears in prose somewhere and asserts it exactly.
A failure does not mean the code broke — it most likely means Cricsheet published another
season and the *document* is now wrong. Fix the document, then the number here.

This is not analysis in the package: ADR 0006 keeps aggregation out of `src/`, and these
are regression guards over a written claim, in `tests/`, marked `integration` so they never
run in the default offline suite. They exist because ADR 0006 names untested analysis as a
real and unmitigated gap, and a stated number is the part of it worth guarding.

Measured against the archive downloaded 2026-08-11.
"""

from __future__ import annotations

import pandas as pd
import pytest

from scorebook import clean
from scorebook.data import loaders

pytestmark = pytest.mark.integration

# Overs are zero-indexed. See clean.add_over.
POWERPLAY = range(0, 6)
MIDDLE = range(6, 15)
DEATH = range(15, 20)
LAST_OVER = 19

# 2009 was played in South Africa and 2020 in the UAE, so nobody was at home.
ABROAD = frozenset({2009, 2020})


@pytest.fixture(scope="session")
def deliveries() -> pd.DataFrame:
    """The real archive, cleaned. Session-scoped: 295k rows is too slow to reload."""
    frame = clean.prepare(loaders.load_deliveries())
    main = clean.drop_unused_categories(frame[frame.innings <= 2])
    return main.assign(total=main.runs_off_bat + main.extras)


@pytest.fixture(scope="session")
def match_info() -> pd.DataFrame:
    info = loaders.load_match_info()
    info = clean.canonical_teams(info, columns=clean.INFO_TEAM_COLUMNS)
    return clean.canonical_venues(info)


def _rate_by_over(deliveries: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Runs and the two denominators: overs reached, and every innings."""
    reaching = (
        deliveries[["match_id", "innings", "over"]]
        .drop_duplicates()
        .groupby("over", observed=True)
        .size()
    )
    runs = deliveries.groupby("over", observed=True)["total"].sum()
    innings = len(deliveries[["match_id", "innings"]].drop_duplicates())
    return runs, reaching, runs / innings


def test_q1_death_overs_beat_the_middle_by_the_stated_margin(deliveries: pd.DataFrame):
    runs, reaching, _ = _rate_by_over(deliveries)

    def phase(overs: range) -> float:
        picked = list(overs)
        return runs[picked].sum() / reaching[picked].sum()

    assert round(phase(DEATH), 2) == 9.78
    assert round(phase(MIDDLE), 2) == 7.94
    assert round(phase(DEATH) - phase(MIDDLE), 2) == 1.84


def test_q1_the_powerplay_ramp_is_steeper_than_the_death_ramp(deliveries: pd.DataFrame):
    """Half of Q1's hypothesis is reported as wrong on the strength of this comparison.
    If it ever flips, results.md is asserting the opposite of the data."""
    runs, reaching, _ = _rate_by_over(deliveries)
    rate = runs / reaching
    powerplay_ramp = (rate[5] - rate[0]) / 5
    death_ramp = (rate[LAST_OVER] - rate[15]) / 4
    assert round(powerplay_ramp, 2) == 0.47
    assert round(death_ramp, 2) == 0.40
    assert powerplay_ramp > death_ramp


def test_q1_the_wrong_denominator_still_inverts_the_last_over(deliveries: pd.DataFrame):
    """The headline entry in "what didn't work". The naive series must keep falling into
    the last over while the correct one keeps rising, or that section is describing a
    mistake nobody can reproduce."""
    runs, reaching, naive = _rate_by_over(deliveries)
    rate = runs / reaching
    assert round(naive[LAST_OVER], 2) == 8.12
    assert round(rate[LAST_OVER], 2) == 10.59
    assert naive[LAST_OVER] < naive[18], "the naive series should fall into the last over"
    assert rate[LAST_OVER] > rate[18], "the correct series should rise into it"

    innings = len(deliveries[["match_id", "innings"]].drop_duplicates())
    assert innings - reaching[LAST_OVER] == 578
    assert round(100 * (1 - reaching[LAST_OVER] / innings), 1) == 23.3


def test_q2_scoring_rose_by_the_stated_amount(deliveries: pd.DataFrame):
    overs = (
        deliveries[["match_id", "innings", "over"]]
        .drop_duplicates()
        .merge(
            deliveries[["match_id", "innings", "season_year"]].drop_duplicates(),
            on=["match_id", "innings"],
        )
        .groupby("season_year", observed=True)
        .size()
    )
    rate = deliveries.groupby("season_year", observed=True)["total"].sum() / overs
    assert round(rate.loc[2008], 2) == 8.24
    assert round(rate.loc[2026], 2) == 9.80
    assert round(100 * (rate.loc[2026] / rate.loc[2008] - 1), 1) == 18.9
    assert rate.idxmin() == 2009, "the season played in South Africa is the low point"


def test_q3_a_first_over_wicket_costs_the_stated_runs(deliveries: pd.DataFrame):
    innings = (
        deliveries.groupby(["match_id", "innings"], observed=True)
        .agg(runs=("total", "sum"))
        .reset_index()
    )
    lost = (
        deliveries[(deliveries.over == 0) & deliveries.wicket_type.notna()]
        [["match_id", "innings"]]
        .drop_duplicates()
        .assign(first_over_wicket=True)
    )
    innings = innings.merge(lost, on=["match_id", "innings"], how="left")
    innings["first_over_wicket"] = innings.first_over_wicket.notna()

    first = innings[innings.innings == 1]
    means = first.groupby("first_over_wicket")["runs"].mean()
    counts = first.groupby("first_over_wicket")["runs"].size()

    assert counts[True] == 199
    assert counts[False] == 1_044
    assert round(means[True], 1) == 158.1
    assert round(means[False], 1) == 170.6
    assert round(means[True] - means[False], 2) == -12.52


def test_q4_the_info_files_still_carry_the_winners(match_info: pd.DataFrame):
    assert len(match_info) == 1_243
    assert match_info.winner.notna().sum() == 1_218
    assert (match_info.outcome == "tie").sum() == 16
    assert (match_info.outcome == "no result").sum() == 9
    assert match_info.venue.nunique() == 36, "60 raw strings collapse to 36 grounds"


def test_q4_home_advantage_matches_the_stated_table(match_info: pd.DataFrame):
    appearances = pd.concat([
        match_info[["match_id", "venue", "winner", side]]
        .assign(year=match_info.start_date.dt.year)
        .rename(columns={side: "team"})
        for side in ("team_1", "team_2")
    ])
    for column in ("team", "venue", "winner"):
        appearances[column] = appearances[column].astype("string")

    domestic = appearances[~appearances.year.isin(ABROAD)]
    home = (
        domestic.groupby(["team", "venue"], observed=True).size().rename("played")
        .reset_index()
        .sort_values(["team", "played"], ascending=[True, False])
        .drop_duplicates("team")
    )
    decided = domestic[domestic.winner.notna()].merge(
        home[["team", "venue"]].rename(columns={"venue": "home"}), on="team", how="left"
    )
    decided = decided.assign(
        at_home=decided.venue == decided.home, won=decided.winner == decided.team
    )

    assert round(decided[decided.at_home].won.mean(), 3) == 0.533
    assert round(decided[~decided.at_home].won.mean(), 3) == 0.482

    sunrisers = decided[decided.team == "Sunrisers Hyderabad"]
    advantage = (
        sunrisers[sunrisers.at_home].won.mean() - sunrisers[~sunrisers.at_home].won.mean()
    )
    assert round(advantage, 3) == 0.195, "the largest home advantage in results.md"
    assert sunrisers[sunrisers.at_home].venue.iloc[0] == "Rajiv Gandhi International Stadium"


def test_q5_wides_are_rising_and_no_balls_are_falling(deliveries: pd.DataFrame):
    """Q5 is reported as falsified. The direction is the finding, so it is what to pin."""
    by_season = deliveries.groupby("season_year", observed=True).agg(
        balls=("total", "size"), wides=("wides", "sum"), noballs=("noballs", "sum")
    )
    wide_rate = by_season.wides / by_season.balls * 100
    noball_rate = by_season.noballs / by_season.balls * 100
    years = pd.Series(by_season.index, index=by_season.index).astype(float)

    assert round(wide_rate.loc[2008], 2) == 4.42
    assert round(wide_rate.loc[2026], 2) == 5.20
    assert wide_rate.idxmax() == 2026
    assert round(noball_rate.loc[2008], 2) == 0.61
    assert round(noball_rate.loc[2026], 2) == 0.36
    assert wide_rate.corr(years) > 0, "wides rise, which is what falsifies Q5"
    assert noball_rate.corr(years) < 0

    # The second falsification condition: the noise is nearly the size of the drift.
    assert round(wide_rate.std(), 2) == 0.62
    assert round(wide_rate.loc[2026] - wide_rate.loc[2008], 2) == 0.78
