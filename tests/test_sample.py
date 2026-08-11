"""The committed sample is an artefact with invariants, so it gets tested like one.

`data/sample_deliveries.csv` is the only data in the repository, and it is what makes a
fresh clone work offline. It is stratified on purpose — the first IPL match and the most
recent one — so that it carries both `season` formats and both generations of team names.

A random sample would carry neither, and every cleaning test that runs against it would be
proving nothing. These tests assert the properties the sample is *for*, rather than its row
count, which changes legitimately whenever a new season is published.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scorebook import clean
from scorebook.data import loaders

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_deliveries.csv"

# Cricsheet writes a straddling season as "2007/08" and a single-year one as "2026".
_SLASH_SEASON = re.compile(r"^\d{4}/\d{2}$")
_PLAIN_SEASON = re.compile(r"^\d{4}$")


@pytest.fixture
def sample():
    if not SAMPLE.exists():  # pragma: no cover - only if the sample is deleted
        pytest.fail(f"{SAMPLE} is missing; regenerate with scripts/make_sample.py")
    return loaders.load_sample(SAMPLE)


def test_sample_loads_and_holds_two_matches(sample):
    assert sample["match_id"].nunique() == 2
    assert len(sample) > 0


def test_sample_carries_both_season_formats(sample):
    """The reason the sample is stratified rather than random.

    Asserting only "two distinct seasons" would pass on two plain-year seasons and prove
    nothing about the parsing this sample exists to exercise.
    """
    seasons = {str(value) for value in sample["season"].unique()}
    assert any(_SLASH_SEASON.match(s) for s in seasons), (
        f"no straddling season (e.g. 2007/08) in {sorted(seasons)} — "
        "the sample no longer exercises the season-label trap"
    )
    assert any(_PLAIN_SEASON.match(s) for s in seasons), (
        f"no single-year season in {sorted(seasons)}"
    )


def test_sample_carries_a_pre_rename_team_name(sample):
    """So the canonicalisation in clean.prepare is actually exercised offline."""
    teams = set(sample["batting_team"]) | set(sample["bowling_team"])
    renamed = teams & clean.TEAM_RENAMES.keys()
    assert renamed, (
        f"no pre-rename team name in {sorted(teams)} — clean.canonical_teams does "
        "nothing on this sample, so the offline tests stop covering it"
    )


def test_sample_survives_the_full_cleaning_pipeline(sample):
    prepared = clean.prepare(sample)
    assert {"season_year", "over"} <= set(prepared.columns)
    # Both eras present: the first IPL season and a recent one.
    years = prepared["season_year"]
    assert years.min() == 2008
    assert years.max() >= 2026
    # The rename collapsed at least one pair, so fewer distinct teams than raw names.
    raw_names = len(set(sample["batting_team"]) | set(sample["bowling_team"]))
    clean_names = len(set(prepared["batting_team"]) | set(prepared["bowling_team"]))
    assert clean_names < raw_names


def test_sample_start_date_parses_to_datetime(sample):
    assert sample["start_date"].dtype.kind == "M"
