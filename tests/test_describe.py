"""Dataset summary — what the CI smoke job asserts against."""

from __future__ import annotations

from scorebook import describe
from scorebook.data import loaders


def test_summarise_counts_rows_matches_and_seasons(sample_csv):
    summary = describe.summarise(loaders.load_sample(sample_csv))
    assert summary.rows == 4
    assert summary.matches == 2
    assert summary.seasons == 2
    assert summary.first_date == "2008-04-18"
    assert summary.last_date == "2026-03-28"
    assert summary.memory_mib >= 0


def test_null_profile_ranks_emptiest_first(sample_csv):
    nulls = describe.null_profile(loaders.load_sample(sample_csv))
    assert nulls.iloc[0] >= nulls.iloc[-1]
    # 3 of 4 rows have no wicket.
    assert nulls["wicket_type"] == 75.0
    assert nulls["match_id"] == 0.0


def test_format_summary_reports_every_field(sample_csv):
    frame = loaders.load_sample(sample_csv)
    text = describe.format_summary(describe.summarise(frame))
    for label in ("rows", "columns", "matches", "seasons", "dates", "memory"):
        assert label in text
    assert "null %" not in text, "nulls are opt-in"


def test_format_summary_includes_nulls_when_given_them(sample_csv):
    frame = loaders.load_sample(sample_csv)
    text = describe.format_summary(describe.summarise(frame), describe.null_profile(frame))
    assert "null %" in text
    assert "wicket_type" in text
    # Columns with no nulls are noise in that list.
    assert "match_id" not in text.split("null %")[1]
