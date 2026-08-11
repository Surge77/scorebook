"""The per-match metadata files. Offline: the archive fixture carries synthetic ones."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pandas as pd
import pytest

from scorebook import clean
from scorebook.data import loaders, schemas


def test_key_value_rows_become_one_row_per_match(archive: Path, cache_dir: Path):
    """The files are long format. Read tabularly they yield three unnamed columns of
    mixed meaning, so the pivot is the whole point of the loader."""
    assert archive.exists()
    info = loaders.load_match_info(cache_dir, download=False)
    assert len(info) == 2
    assert list(info.columns) == list(schemas.INFO_COLUMNS)
    assert info["match_id"].tolist() == [1, 2]


def test_the_two_team_rows_fold_into_team_1_and_team_2(archive: Path, cache_dir: Path):
    """`team` is the one repeated key that carries distinct values rather than a
    correction, so it widens instead of collapsing."""
    assert archive.exists()
    info = loaders.load_match_info(cache_dir, download=False).set_index("match_id")
    assert info.loc[1, "team_1"] == "Mumbai Indians"
    assert info.loc[1, "team_2"] == "Kings XI Punjab"


def test_a_reserve_day_second_date_does_not_become_the_start_date(
    archive: Path, cache_dir: Path
):
    """Two matches in the real archive carry a second `date` row for a reserve day.
    Taking the last would date the match a day after its deliveries."""
    assert archive.exists()
    info = loaders.load_match_info(cache_dir, download=False).set_index("match_id")
    assert info.loc[2, "start_date"] == pd.Timestamp("2008-04-18")


def test_slash_separated_dates_parse(archive: Path, cache_dir: Path):
    """The info files write 2026/03/28 where all_matches.csv writes 2026-03-28. One
    archive, two formats, nothing upstream saying so."""
    assert archive.exists()
    info = loaders.load_match_info(cache_dir, download=False)
    assert info["start_date"].dtype.kind == "M"
    assert info.set_index("match_id").loc[1, "start_date"] == pd.Timestamp("2026-03-28")


def test_a_tie_has_no_winner_but_keeps_its_eliminator(archive: Path, cache_dir: Path):
    """25 real matches have no `winner`: 16 ties and 9 no-results. Dropping the null
    would silently discard the 16 that were in fact decided, by super over."""
    assert archive.exists()
    info = loaders.load_match_info(cache_dir, download=False).set_index("match_id")
    assert pd.isna(info.loc[2, "winner"])
    assert info.loc[2, "outcome"] == "tie"
    assert info.loc[2, "eliminator"] == "Royal Challengers Bangalore"


def test_the_undecided_margin_column_is_null_not_zero(archive: Path, cache_dir: Path):
    """`winner_runs` and `winner_wickets` are mutually exclusive. A 0 in the one that did
    not decide the match would read as 'won by zero wickets'."""
    assert archive.exists()
    info = loaders.load_match_info(cache_dir, download=False).set_index("match_id")
    assert info.loc[1, "winner_runs"] == 12
    assert pd.isna(info.loc[1, "winner_wickets"])


def test_player_and_registry_rows_are_ignored(archive: Path, cache_dir: Path):
    """A real file holds 22 `player` rows and ~50 `registry` rows. Folding them in would
    multiply the grain and stop the frame being one row per match."""
    assert archive.exists()
    info = loaders.load_match_info(cache_dir, download=False)
    assert len(info) == 2, "the grain is the match, not the player"
    assert not {"player", "registry", "umpire"} & set(info.columns)
    # A `player` row is `info,player,<team>,<name>` — its third field is a team name, and
    # reading it positionally would overwrite the real value.
    assert info.set_index("match_id").loc[1, "player_of_match"] == "RG Sharma"


def test_a_member_without_a_match_id_names_the_file(
    cache_dir: Path, make_archive: Callable[..., Path]
):
    """Without match_id the row cannot be joined to the deliveries, so it must fail by
    name rather than produce a frame that is quietly one match short."""
    make_archive(cache_dir, info={"99_info.csv": b"version,2.3.0\ninfo,venue,Somewhere\n"})
    with pytest.raises(schemas.SchemaError, match=r"99_info\.csv"):
        loaders.load_match_info(cache_dir, download=False)


def test_an_archive_without_info_members_fails_loudly(
    cache_dir: Path, make_archive: Callable[..., Path]
):
    make_archive(cache_dir, info={})
    with pytest.raises(schemas.SchemaError, match=r"_info\.csv"):
        loaders.load_match_info(cache_dir, download=False)


def test_refuses_to_download_when_told_not_to(cache_dir: Path):
    with pytest.raises(loaders.DownloadError, match="scorebook fetch"):
        loaders.load_match_info(cache_dir, download=False)


def test_canonical_teams_renames_the_info_columns(archive: Path, cache_dir: Path):
    """The info files carry pre-rename names too. Counting Delhi Daredevils and Delhi
    Capitals apart splits one franchise across two rows of any winner table."""
    assert archive.exists()
    info = loaders.load_match_info(cache_dir, download=False)
    renamed = clean.canonical_teams(info, columns=clean.INFO_TEAM_COLUMNS).set_index(
        "match_id"
    )
    assert renamed.loc[2, "team_1"] == "Royal Challengers Bengaluru"
    assert renamed.loc[2, "team_2"] == "Delhi Capitals"
    assert renamed.loc[2, "toss_winner"] == "Delhi Capitals"


def test_canonical_teams_leaves_a_null_winner_null(archive: Path, cache_dir: Path):
    """`replace` over a categorical round-trips through string. A null must survive it —
    the tie has no winner, and inventing one would fabricate a result."""
    assert archive.exists()
    info = loaders.load_match_info(cache_dir, download=False)
    renamed = clean.canonical_teams(info, columns=clean.INFO_TEAM_COLUMNS)
    assert renamed["winner"].isna().sum() == 1


def test_canonical_teams_still_defaults_to_the_delivery_columns(sample_csv: Path):
    """The new `columns` argument must not change what `prepare()` already does."""
    frame = loaders.load_sample(sample_csv)
    renamed = clean.canonical_teams(frame)
    assert "Royal Challengers Bengaluru" in set(renamed["batting_team"])
    assert "Royal Challengers Bangalore" not in set(renamed["batting_team"])
